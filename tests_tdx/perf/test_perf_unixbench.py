"""
Do performance measuring and comparition for UnixBench test between legacy VM and TDVM.
"""
import os
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD_PERF, VM_TYPE_EFI_PERF, VMSpec

__author__ = 'cpio'

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-pts-image"),    # from artifacts.yaml
]


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD_PERF, VM_TYPE_EFI_PERF])
def test_unixbench(vm_factory, vm_ssh_key, vm_ssh_pubkey, vm_type,
                   output):
    """
    Collect UnixBench performance

    1. use the bench script unix-bench-perf.sh
    2. the result will be put into output/unixbench-perf-xxxx directory

    """
    LOG.info("Create guest to run UnixBench benchmark")
    td_inst = vm_factory.new_vm(vm_type, vmspec=VMSpec.model_large())

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "unix-bench-perf.sh"), "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    if vm_type is VM_TYPE_TD_PERF:
        dir_name = "/tmp/unixbench-perf-tdvm"
    else:
        dir_name = "/tmp/unixbench-perf-legacy"

    # Enable cpuidle-haltpoll driver in VM
    command = "modprobe cpuidle-haltpoll force=Y"
    runner = td_inst.ssh_run(command.split(), vm_ssh_key)
    assert runner.retcode == 0, "Fail to enable cpuidle_haulpoll driver in guest VM."

    td_inst.ssh_run(['mkdir -p ' + dir_name], vm_ssh_key)

    command_list = [
        f'/root/unix-bench-perf.sh -o {dir_name} -r 1'
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    td_inst.destroy()
    td_inst.image.copy_out(f"{dir_name}", output)
