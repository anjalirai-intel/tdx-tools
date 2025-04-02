"""
This module provide the case to test 2 socket boot

"""

import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_STATE_RUNNING, VM_TYPE_EFI, VM_TYPE_TD, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.regression
@pytest.mark.nontme
def test_legacy_2_socket(vm_factory):
    """
    Test boot legacy guest with 2 sockets
    """
    LOG.info("Create Legacy guest")
    inst = vm_factory.new_vm(VM_TYPE_LEGACY, vmspec=VMSpec.model_numa())

    # create and start VM instance
    inst.create()
    inst.start()
    assert inst.wait_for_state(VM_STATE_RUNNING), "Boot fail"
    assert inst.wait_for_ssh_ready(), "Boot timeout"


@pytest.mark.regression
def test_efi_2_socket(vm_factory):
    """
    Test boot efi guest with 2 sockets
    """
    LOG.info("Create EFI guest")
    inst = vm_factory.new_vm(VM_TYPE_EFI, vmspec=VMSpec.model_numa())

    # create and start VM instance
    inst.create()
    inst.start()
    assert inst.wait_for_state(VM_STATE_RUNNING), "Boot fail"
    assert inst.wait_for_ssh_ready(), "Boot timeout"


@pytest.mark.regression
def test_td_2_socket(vm_factory):
    """
    Test boot TD guest with 2 sockets
    """
    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=VMSpec.model_numa())

    # create and start VM instance
    inst.create()
    inst.start()
    assert inst.wait_for_state(VM_STATE_RUNNING), "Boot fail"
    assert inst.wait_for_ssh_ready(), "Boot timeout"
