"""
Call "poweroff" command within VM
"""

import logging
import time
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_STATE_SHUTDOWN, VM_TYPE_EFI, VM_TYPE_TD
from pycloudstack.vmguest import VirshSSH

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_tdvm_acpi_shutdown(vm_factory):
    """
    Test ACPI shutdown for TD guest
    """
    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD)

    # create and start VM instance
    inst.create()
    inst.start()
    
    qm = VirshSSH(inst)
    qm.poweroff()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_SHUTDOWN), "shutdown fail"

def test_efi_acpi_shutdown(vm_factory):
    """
    Test ACPI shutdown for EFI guest
    """
    LOG.info("Create EFI guest")
    inst = vm_factory.new_vm(VM_TYPE_EFI)

    # create and start VM instance
    inst.create()
    inst.start()

    qm = VirshSSH(inst)
    qm.poweroff()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_SHUTDOWN), "shutdown fail"

def test_legacy_acpi_shutdown(vm_factory):
    """
    Test ACPI shutdown for legacy VM
    """
    LOG.info("Create legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_LEGACY)

    # create and start VM instance
    inst.create()
    inst.start()

    qm = VirshSSH(inst)
    qm.poweroff()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_SHUTDOWN), "shutdown fail"
