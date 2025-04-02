"""
This module provide the case to test the lifecyle for TD/EFI/Legacy guest via
Qemu operator.

"""

import logging
import time
import pytest
from gpl.vmmqmp import VMMQemu
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY, VM_TYPE_EFI, VM_STATE_RUNNING

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_legacyguest_reboot_qemu(vm_factory):
    """
    Test reboot for legacy guest via Qemu operator
    """
    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_LEGACY, vm_class=VMMQemu, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Reboot Legacy guest")
    inst.reboot()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    assert inst.wait_for_ssh_ready(), "Reboot timeout"


def test_efi_reboot_qemu(vm_factory):
    """
    Test reboot for EFI guest via Qemu operator
    """
    LOG.info("Create EFI guest")
    inst = vm_factory.new_vm(VM_TYPE_EFI, vm_class=VMMQemu, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Reboot EFI guest")
    inst.reboot()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    assert inst.wait_for_ssh_ready(), "Reboot timeout"


def test_td_reboot_qemu(vm_factory):
    """
    Test reboot for TD guest via Qemu operator
    """
    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, vm_class=VMMQemu, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Reboot TD guest")
    inst.reboot()

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_RUNNING), "Reboot fail"
    assert inst.wait_for_ssh_ready(), "Reboot timeout"
