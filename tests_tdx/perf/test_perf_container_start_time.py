"""
Do performance measuring and comparition for container start time between legacy VM and TDVM.
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


def test_tdvm_container_start_time(vm_factory, vm_ssh_key, vm_ssh_pubkey,
                                   output):
    """
    Collect container start time performance for TD guest

    1. use the bench script container-start-perf.sh
    2. the result will be put into output/container-perf-tdvm directory

    """
    LOG.info("Create TD guest to run container start time benchmark")
    td_inst = vm_factory.new_vm(VM_TYPE_TD_PERF, vmspec=VMSpec.model_large())

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "container-start-perf.sh"), "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    command_list = [
        'systemctl start docker',
        '/root/container-start-perf.sh -o /tmp/container-perf-tdvm/ -r 1000'
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    td_inst.destroy()
    td_inst.image.copy_out("/tmp/container-perf-tdvm/", output)


def test_legacy_container_start_time(vm_factory, vm_ssh_key, vm_ssh_pubkey,
                                     output):
    """
    Collect container start time performance for legacy guest

    1. use the bench script container-start-perf.sh
    2. the result will be put into output/container-perf-legacy directory

    """

    LOG.info("Create TD guest to run container start time benchmark")
    vm_inst = vm_factory.new_vm(VM_TYPE_EFI_PERF, vmspec=VMSpec.model_large())

    # customize the VM image
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "container-start-perf.sh"), "/root/")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"

    command_list = [
        'systemctl start docker',
        '/root/container-start-perf.sh -o /tmp/container-perf-legacy/ -r 1000'
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.destroy()
    vm_inst.image.copy_out("/tmp/container-perf-legacy/", output)
