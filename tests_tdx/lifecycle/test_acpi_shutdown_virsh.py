"""
Call "reboot" command within VM
"""

import logging
import time
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_STATE_SHUTDOWN, VM_TYPE_EFI, VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.regression
@pytest.mark.nontme
def test_legacyguest_acpi_shutdown_virsh(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Test ACPI shutdown for legacy guest
    """
    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_LEGACY)
    inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    inst.create()
    inst.start()
    assert inst.wait_for_ssh_ready()

    inst.ssh_run(["poweroff"], vm_ssh_key)

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_SHUTDOWN), "shutdown fail"


@pytest.mark.regression
def test_efiguest_acpi_shutdown_virsh(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Test ACPI shutdown for efi guest
    """
    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_EFI)
    inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    inst.create()
    inst.start()
    assert inst.wait_for_ssh_ready()

    inst.ssh_run(["poweroff"], vm_ssh_key)

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_SHUTDOWN), "shutdown fail"


@pytest.mark.regression
def test_tdguest_acpi_shutdown_virsh(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Test ACPI shutdownreboot for TD guest
    """
    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_TD)
    inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    inst.create()
    inst.start()
    assert inst.wait_for_ssh_ready()

    inst.ssh_run(["poweroff"], vm_ssh_key)

    # Sleep for a while for shutdown first
    time.sleep(5)
    assert inst.wait_for_state(VM_STATE_SHUTDOWN), "shutdown fail"
