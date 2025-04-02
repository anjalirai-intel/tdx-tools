"""
Do performance measuring and comparition for disk fio test between legacy VM and TDVM.
"""
import os
import logging
import datetime
import time
import pytest

from pycloudstack.vmparam import VM_TYPE_TD_PERF, VM_TYPE_EFI_PERF, VMSpec
from pycloudstack.cmdrunner import NativeCmdRunner

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

cache_list = [('native', 'none'), ('threads', 'writethrough')]


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD_PERF, VM_TYPE_EFI_PERF])
@pytest.mark.parametrize("rw,iodepth,bs", config_list)
@pytest.mark.parametrize("io_mode,cache", cache_list)
def test_disk_fio(vm_factory, vm_ssh_key, vm_ssh_pubkey, vm_type, rw, iodepth, bs, io_mode, cache, output):
    """
    Collect disk fio performance for TD and legacy guest

    """
    LOG.info("Create guest to run disk fio benchmark")

    # create disk file if the same size disk file doesn't exist
    # diskfile size with unit GB
    diskfile_size = 30
    diskfile_path = os.path.join(CURR_DIR, "../../cache/data_disk.qcow2")
    if os.path.exists(diskfile_path):
        exist_diskfile_size = int(os.path.getsize(diskfile_path) / 1024 / 1024 / 1024)
        if exist_diskfile_size != diskfile_size:
            os.remove(diskfile_path)
            runner = NativeCmdRunner(["qemu-img", "create", "-o", "preallocation=full", "-f", "qcow2", diskfile_path,
                                     f"{diskfile_size}G"])
            assert runner.runwait() == 0
    else:
        runner = NativeCmdRunner(["qemu-img", "create", "-o", "preallocation=full", "-f", "qcow2", diskfile_path,
                                 f"{diskfile_size}G"])
        assert runner.runwait() == 0

    td_inst = vm_factory.new_vm(vm_type, vmspec=VMSpec.model_large(), io_mode=io_mode, cache=cache,
                                diskfile_path=diskfile_path)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "fio_report.job"), "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    if vm_type is VM_TYPE_TD_PERF:
        dir_name = "/tmp/fio-perf-tdvm"
    else:
        dir_name = "/tmp/fio-perf-legacy"

    td_inst.ssh_run(['mkdir -p ' + dir_name], vm_ssh_key)

    guest_cmd = f'IODEPTH={iodepth} BS={bs} RW={rw} ' + \
                f'fio /root/fio_report.job >> {dir_name}/{cache}-{iodepth}-{bs}-{rw}-{DATE_SUFFIX}.txt'
    LOG.debug(guest_cmd)

    # flush cache in td guest
    runner = td_inst.ssh_run(['echo 3 > /proc/sys/vm/drop_caches'], vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    time.sleep(5)

    # flush cache on host
    ssh_runner = NativeCmdRunner('echo 3 > /proc/sys/vm/drop_caches'.split())
    ssh_runner.runwait()
    assert ssh_runner.retcode == 0, "Fail to execute native cache flush command on host"

    time.sleep(5)

    NativeCmdRunner('free -h'.split()).runwait()

    runner = td_inst.ssh_run(guest_cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    runner = td_inst.ssh_run(['sync'], vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    time.sleep(5)

    td_inst.destroy()
    td_inst.image.copy_out(f"{dir_name}", output)
