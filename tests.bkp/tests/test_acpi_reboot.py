"""
Call "reboot" command within VM
"""

import logging
import time
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_STATE_RUNNING, VM_TYPE_EFI, VM_TYPE_TD
from pycloudstack.vmguest import VirshSSH

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_tdvm_acpi_reboot(vm_factory):
    """
    Test ACPI reboot for TDVM
    """
    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD)
    
    # create and start VM instance
    inst.create()
    inst.start()

    qm = VirshSSH(inst)
    qm.check_exec("shutdown -r now")
    qm.close()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    qm = VirshSSH(inst)
    qm.close()

def test_efi_acpi_reboot(vm_factory):
    """
    Test ACPI reboot for EFI VM
    """
    LOG.info("Create EFI guest")
    inst = vm_factory.new_vm(VM_TYPE_EFI)

    # create and start VM instance
    inst.create()
    inst.start()

    qm = VirshSSH(inst)
    qm.check_exec("shutdown -r now")
    qm.close()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    qm = VirshSSH(inst)
    qm.close()

def test_legacy_acpi_reboot(vm_factory):
    """
    Test ACPI reboot for legacy VM
    """
    LOG.info("Create legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_LEGACY)

    # create and start VM instance
    inst.create()
    inst.start()

    qm = VirshSSH(inst)
    qm.check_exec("shutdown -r now")
    qm.close()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    qm = VirshSSH(inst)
    qm.close()
    