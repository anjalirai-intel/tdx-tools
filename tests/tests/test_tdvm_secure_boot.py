"""
This module provides the case to test if Secure Boot is enabled inside the TD VM.
"""

import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD_SB

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_tdguest_with_secure_boot(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Test the different type VM run parallel

    Test Steps
    ----------
    1. Launch a TD guest with Secure Boot enabled
    """

    LOG.info("Create a Secure Boot enabled TD guest")
    td_inst = vm_factory.new_vm(VM_TYPE_TD_SB)
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    td_inst.create()
    td_inst.start()

    assert td_inst.wait_for_ssh_ready(), "Could not reach TD VM"

    LOG.info("Test if Secure Boot is enabled in TD guest")
    command = "dmesg | grep -i 'Secure Boot'"

    runner = td_inst.ssh_run(command.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    LOG.info(runner.stdout[0])
    assert "Secure boot enabled" in runner.stdout[0], "Secure Boot failed in the guest!"
