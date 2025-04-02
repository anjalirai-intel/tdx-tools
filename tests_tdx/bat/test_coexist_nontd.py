"""
This module provide the case to test the coexistance between TDX guest and non TD
guest. There are two type non-TD guest:

1. Boot with legacy BIOS, it is default loader without pass "-loader" or "-bios"
   option
2. Boot with OVMF UEFI BIOS, will boot with "-loader" => OVMFD.fd compiled from
   the latest edk2 project.

Since the testing focus on compatibilty for VMX, so all cases will only consider
direct boot but not grub boot.

Implemented:
    - Case 1: Test create/destroy for TD/legacy/OVMF VM

TBD:
    - Case 2: Test running same simple workloader for TD/legacy/OVMF VM
    - Case 3: Test running heavy workloader for TD/legacy/OVMF VM
    - Case 4: Test the network traffic between TD/legacy/OVMF VM

"""

import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_TYPE_EFI, VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.smoke
@pytest.mark.bat
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

    assert td_inst.wait_for_ssh_ready(), "Could not reach TD VM"
    assert legacy_inst.wait_for_ssh_ready(), "Could not reach legacy VM"
    assert efi_inst.wait_for_ssh_ready(), "Could not reach EFI VM"
