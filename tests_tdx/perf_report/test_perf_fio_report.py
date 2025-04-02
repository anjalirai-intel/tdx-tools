"""
Do performance measuring and comparition for disk fio test between legacy VM and TDVM.
"""
import os
import logging
import pytest
import datetime
import time
from multiprocessing import Process
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI, VMSpec
from pycloudstack.cmdrunner import NativeCmdRunner, SSHCmdRunner

__author__ = 'cpio'

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-pts-image"),    # from artifacts.yaml
]

config_list = [('randread', 64, '4k'), ('randwrite', 64, '4k'),
               ('read', 64, '64k'), ('write', 64, '64k')]


def collect_host_sar_results(vm_type, output, iodepth, bs, rw):
    cmd = f'sar -A -o /fio-test/{vm_type}_sar_{iodepth}_{bs}_{rw}_{DATE_SUFFIX}.out 10 30'
    LOG.info(cmd)

    native_runner = NativeCmdRunner(cmd.split())
    native_runner.runwait()
    if native_runner.retcode != 0:
        LOG.warning("Fail to execute native command sar")


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD, VM_TYPE_EFI])
@pytest.mark.parametrize("rw,iodepth,bs", config_list)
def test_disk_fio(vm_factory, vm_ssh_key, vm_ssh_pubkey, vm_type, rw, iodepth, bs, output):
    """
    Collect disk fio performance for TD and legacy guest

    """
    LOG.info("Create guest to run disk fio benchmark")
    td_inst = vm_factory.new_vm(vm_type, vmspec=VMSpec.model_large())

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "fio_report.job"), "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    if vm_type is VM_TYPE_TD:
        dir_name = "/tmp/fio-perf-tdvm"
    else:
        dir_name = "/tmp/fio-perf-legacy"

    td_inst.ssh_run(['mkdir -p ' + dir_name], vm_ssh_key)

    guest_cmd = f'IODEPTH={iodepth} BS={bs} RW={rw} taskset 0x1 ' + \
                f'fio /root/fio_report.job >> {dir_name}/{iodepth}-{bs}-{rw}-{DATE_SUFFIX}.txt'
    LOG.debug(guest_cmd)

    guest_sar_cmd = \
        f'sar -A -o {dir_name}/{vm_type}_guest_sar_{iodepth}_{bs}_{rw}_{DATE_SUFFIX}.out 10 30 >/dev/null 2>&1 &'
    LOG.debug(guest_sar_cmd)

    runner = td_inst.ssh_run(['echo 3 > /proc/sys/vm/drop_caches'], vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    time.sleep(5)

    ssh_runner = SSHCmdRunner('echo 3 > /proc/sys/vm/drop_caches'.split(), '/home/haibo/root_id_rsa', '22')
    ssh_runner.runwait()
    if ssh_runner.retcode != 0:
        LOG.warning("Fail to execute native cache flush command")

    time.sleep(5)

    NativeCmdRunner('free -h'.split()).runwait()

    p = Process(target=collect_host_sar_results, args=(vm_type, output, iodepth, bs, rw))
    p.start()

    runner = td_inst.ssh_run(guest_sar_cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    runner = td_inst.ssh_run(guest_cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    runner = td_inst.ssh_run(['sync'], vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    p.join()

    time.sleep(5)

    td_inst.destroy()
    td_inst.image.copy_out(f"{dir_name}", output)
