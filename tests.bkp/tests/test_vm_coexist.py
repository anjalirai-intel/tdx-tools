"""
This module provide the case to test the coexistance between TDX guest and non TD
guest. There are two types of non-TD guest:

1. Boot with legacy BIOS, it is default loader without pass "-loader" or "-bios"
   option
2. Boot with OVMF UEFI BIOS, will boot with "-loader" => OVMFD.fd compiled from
   the latest edk2 project.
"""

import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_TYPE_EFI, VM_TYPE_TD
from pycloudstack.vmguest import VirshSSH

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_tdguest_with_legacy_base(vm_factory):
    """
    Test the different type VM run parallel

    Test Steps
    ----------
    1. Launch a TD guest
    2. Launch a legacy guest
    3. Launch an OVMF guest
    """
    LOG.info("Create a TD guest")
    td_inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True)

    LOG.info("Create a legacy guest")
    legacy_inst = vm_factory.new_vm(VM_TYPE_LEGACY, auto_start=True)

    LOG.info("Create an OVMF guest")
    efi_inst = vm_factory.new_vm(VM_TYPE_EFI, auto_start=True)

    q1 = VirshSSH(td_inst)
    q2 = VirshSSH(legacy_inst)
    q3 = VirshSSH(efi_inst)

    assert q1.ssh_conn != None, "Could not reach TD VM"
    assert q2.ssh_conn != None, "Could not reach legacy VM"
    assert q3.ssh_conn != None, "Could not reach EFI VM"

    q1.close()
    q2.close()
    q3.close()
