"""
Measure the Timestamp counter for TD guest
"""
import logging
from datetime import datetime
import pytest
from pycloudstack.vmparam import VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),
    pytest.mark.vm_image("latest-guest-image"),
]


def test_tdvm_tsc(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Collect nginx performance for TD guest

    1. run tsc-test.sh 5 rounds on remote device
    2. check each duration, which should < 5% x 60(s) = 3
    """
    LOG.info("Test Guest TSC")
    td_inst = vm_factory.new_vm(VM_TYPE_TD)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    command_list = [
        'time sleep 60'
    ]

    for index in range(5):
        dt_start = datetime.now()
        for cmd in command_list:
            runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
            assert runner.retcode == 0, "Failed to execute remote command"
        dt_end = datetime.now()

        LOG.info("[%d] total duration is %d",
                 index, (dt_end - dt_start).total_seconds())
        assert (dt_end - dt_start).total_seconds() < 63
