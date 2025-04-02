"""
This module provide the case to test the lifecyle for TD/EFI/Legacy guest via
Qemu operator.

"""

import logging
import pytest
from gpl.vmmqmp import VMMQemu
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY, VM_TYPE_EFI, VM_STATE_SHUTDOWN

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

VM_SHUTDOWN_TIMEOUT = 30


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_legacyguest_shutdown_qemu(vm_factory):
    """
    Test shutdown for legacy guest via Qemu operator
    """
    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_LEGACY, vm_class=VMMQemu,
                             auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Shutdown Legacy guest")
    inst.shutdown()
    ret = inst.wait_for_state(VM_STATE_SHUTDOWN, VM_SHUTDOWN_TIMEOUT)
    assert ret, "Shutdown timeout"


def test_tdguest_shutdown_qemu(vm_factory):
    """
    Test shutdown for TD guest via Qemu operator
    """
    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, vm_class=VMMQemu,
                             auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Shutdown TD guest")
    inst.shutdown()
    ret = inst.wait_for_state(VM_STATE_SHUTDOWN)
    assert ret, "Shutdown timeout"


def test_efiguest_shutdown_qemu(vm_factory):
    """
    Test shutdown for EFI guest via Qemu operator
    """
    LOG.info("Create EFI guest")
    inst = vm_factory.new_vm(VM_TYPE_EFI, vm_class=VMMQemu,
                             auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Shutdown EFI guest")
    inst.shutdown()
    ret = inst.wait_for_state(VM_STATE_SHUTDOWN)
    assert ret, "Shutdown timeout"
