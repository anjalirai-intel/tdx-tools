"""
This module provides the case to test if Secure Boot is enabled inside the TD VM.
"""

import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD_SB
from pycloudstack.vmguest import VirshSSH

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_tdguest_with_secure_boot(vm_factory):
    """
    Test the different type VM run parallel

    Test Steps
    ----------
    1. Launch a TD guest with Secure Boot enabled
    """

    LOG.info("Create a Secure Boot enabled TD guest")
    td_inst = vm_factory.new_vm(VM_TYPE_TD_SB)

    # create and start VM instance
    td_inst.create()
    td_inst.start()

    qm = VirshSSH(td_inst)

    LOG.info("Test if Secure Boot is enabled in TD guest")
    command = "dmesg | grep -i 'Secure Boot'"

    stdout, stderr = qm.check_exec(command)
    qm.close()

    LOG.info(stdout)
    assert "Secure boot enabled" in stdout, "Secure Boot failed in the guest!"
