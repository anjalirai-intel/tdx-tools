"""
This test module tests QEMU Guest Agent command to reboot Legacy/EFI/TD Guest:
{"execute":"guest-shutdown", "arguments": { "mode": "reboot" }}
"""

import logging
import time
import pytest
from libvirt import libvirtError, VIR_ERR_AGENT_UNRESPONSIVE

from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY, VM_TYPE_EFI

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_legacy_qga_reboot(vm_factory):
    """
    Test rebooting a Legacy guest using QEMU Guest Agent command

    Step 1: Create Legacy guest
    Step 2: Send command to QEMU Guest agent to reboot the Legacy guest
    """

    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_LEGACY, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Request QEMU Guest Agent to reboot the Legacy guest")
    # QEMU Guest Agent reboots the Legacy guest down abruptly, checking
    # for VM state does not work.
    try:
        inst.vmm.qemu_agent_reboot()
    except libvirtError as e:
        LOG.info(e)
        assert e.get_error_code() == VIR_ERR_AGENT_UNRESPONSIVE, "QEMU Guest Agent reboot fail"

    time.sleep(5)
    assert inst.wait_for_ssh_ready(), "TD Guest did not reboot"


def test_efi_qga_reboot(vm_factory):
    """
    Test rebooting a EFI guest using QEMU Guest Agent command

    Step 1: Create EFI guest
    Step 2: Send command to QEMU Guest agent to reboot the EFI guest
    """

    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_EFI, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Request QEMU Guest Agent to reboot the EFI guest")
    # QEMU Guest Agent reboots the EFI guest down abruptly, checking
    # for VM state does not work.
    try:
        inst.vmm.qemu_agent_reboot()
    except libvirtError as e:
        LOG.info(e)
        assert e.get_error_code() == VIR_ERR_AGENT_UNRESPONSIVE, "QEMU Guest Agent reboot fail"

    time.sleep(5)
    assert inst.wait_for_ssh_ready(), "TD Guest did not reboot"


@pytest.mark.regression
def test_tdvm_qga_reboot(vm_factory):
    """
    Test rebooting a TD guest using QEMU Guest Agent command

    Step 1: Create TD guest
    Step 2: Send command to QEMU Guest agent to reboot the TD guest
    """

    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Request QEMU Guest Agent to reboot the TD guest")
    # QEMU Guest Agent reboots the TD guest down abruptly, checking
    # for VM state does not work.
    try:
        inst.vmm.qemu_agent_reboot()
    except libvirtError as e:
        LOG.info(e)
        assert e.get_error_code() == VIR_ERR_AGENT_UNRESPONSIVE, "QEMU Guest Agent reboot fail"

    time.sleep(10)
    assert inst.wait_for_ssh_ready(), "TD Guest did not reboot"
