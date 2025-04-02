"""
This module provide the case to test the lifecyle for TD/EFI/Legacy guest via
Qemu operator.

"""

import logging
import time
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_STATE_RUNNING, VM_TYPE_EFI, VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.regression
@pytest.mark.nontme
def test_legacyguest_reboot_virsh(vm_factory):
    """
    Test reboot for legacy guest via Virsh operator
    """
    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_LEGACY, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Reboot Legacy guest")
    inst.reboot()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    assert inst.wait_for_ssh_ready(), "Reboot timeout"


@pytest.mark.regression
def test_efi_reboot_virsh(vm_factory):
    """
    Test reboot for EFI guest via Virsh operator
    """
    LOG.info("Create EFI guest")
    inst = vm_factory.new_vm(VM_TYPE_EFI, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Reboot EFI guest")
    inst.reboot()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    assert inst.wait_for_ssh_ready(), "Reboot timeout"


@pytest.mark.regression
def test_td_reboot_virsh(vm_factory):
    """
    Test reboot for TD guest via Virsh operator
    """
    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Reboot TD guest")
    inst.reboot()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    assert inst.wait_for_ssh_ready(), "Reboot timeout"
