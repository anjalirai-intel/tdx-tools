"""
Do performance measuring and comparition for redis-work between legacy VM and TDVM.
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
    pytest.mark.vm_image("latest-pts-image"),
]


def test_tdvm_redis_simple(vm_factory, vm_ssh_key, vm_ssh_pubkey,
                           output):
    """
    Collect redis-bench performance for TD guest

    1. use the bench script redis-bench-perf.sh
    2. warmup 2 rounds then measure 5 times
    3. the result will be put into output/redis-perf-tdvm directory

    """
    LOG.info("Create TD guest to run redis benchmark")
    td_inst = vm_factory.new_vm(VM_TYPE_TD_PERF, vmspec=VMSpec.model_large())

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "redis-bench-perf.sh"), "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    command_list = [
        'systemctl start docker',
        '/root/redis-bench-perf.sh -o /tmp/redis-perf-tdvm/ -w 2 -r 5'
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    td_inst.destroy()
    td_inst.image.copy_out("/tmp/redis-perf-tdvm/", output)


def test_legacy_redis_simple(vm_factory, vm_ssh_key, vm_ssh_pubkey,
                             output):
    """
    Collect redis-bench performance for legacy guest

    1. use the bench script redis-bench-perf.sh
    2. warmup 2 rounds then measure 5 times
    3. the result will be put into output/redis-perf-tdvm directory

    """

    LOG.info("Create TD guest to run redis benchmark")
    vm_inst = vm_factory.new_vm(VM_TYPE_EFI_PERF, vmspec=VMSpec.model_large())

    # customize the VM image
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "redis-bench-perf.sh"), "/root/")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"

    command_list = [
        'systemctl start docker',
        '/root/redis-bench-perf.sh -o /tmp/redis-perf-legacy/ -w 2 -r 5'
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.destroy()
    vm_inst.image.copy_out("/tmp/redis-perf-legacy/", output)
