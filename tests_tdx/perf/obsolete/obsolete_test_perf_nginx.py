"""
Do performance measuring and comparition for nginx between legacy VM and TDVM.
"""
import os
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY

__author__ = 'cpio'

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-test-image"),    # from artifacts.yaml
]


@pytest.mark.skip(reason="The output log is too large")
def test_tdvm_nginx_simple(vm_factory, vm_ssh_key, vm_ssh_pubkey,
                           output):
    """
    Collect nginx performance for TD guest

    1. use the bench script nginx-bench-perf.sh
    2. warmup 2 rounds then measure 5 times
    3. the result will be put into output/nginx-perf-tdvm directory

    """
    LOG.info("Create TD guest to run nginx benchmark")
    td_inst = vm_factory.new_vm(VM_TYPE_TD)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "nginx-bench-perf.sh"), "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    td_inst.wait_for_ssh_ready()

    command_list = [
        'systemctl start docker',
        '/root/nginx-bench-perf.sh -o /tmp/nginx-perf-tdvm/ -w 2 -r 3'
    ]

    for cmd in command_list:
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    td_inst.destroy()
    td_inst.image.copy_out("/tmp/nginx-perf-tdvm/", output)


@pytest.mark.skip(reason="The output log is too large")
def test_legacy_nginx_simple(vm_factory, vm_ssh_key, vm_ssh_pubkey,
                             output):
    """
    Collect nginx-bench performance for legacy guest

    1. use the bench script nginx-bench-perf.sh
    2. warmup 2 rounds then measure 5 times
    3. the result will be put into output/nginx-perf-tdvm directory

    """

    LOG.info("Create TD guest to run nginx benchmark")
    vm_inst = vm_factory.new_vm(VM_TYPE_LEGACY)

    # customize the VM image
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "nginx-bench-perf.sh"), "/root/")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready()

    command_list = [
        'systemctl start docker',
        '/root/nginx-bench-perf.sh -o /tmp/nginx-perf-legacy/ -w 2 -r 5'
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.destroy()
    vm_inst.image.copy_out("/tmp/nginx-perf-legacy/", output)
