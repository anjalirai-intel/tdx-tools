"""
This module provide the case to test the lifecyle for TD/EFI/Legacy guest via
Qemu operator.

"""

import logging
import pytest
from gpl.vmmqmp import VMMQemu
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY, VM_TYPE_EFI, VM_STATE_RUNNING, \
    VM_STATE_PAUSE

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def impl_vm_suspend_resume_qemu(vm_factory, vm_type):
    """
    Test suspend resume for VM guest via Qemu operator
    """
    LOG.info("Create %s guest", vm_type)
    inst = vm_factory.new_vm(vm_type, vm_class=VMMQemu,
                             auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Suspend %s guest", vm_type)
    inst.suspend()
    ret = inst.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    LOG.info("Resume %s guest", vm_type)
    inst.resume()
    ret = inst.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"


@pytest.mark.bat
def test_td_suspend_resume_qemu(vm_factory):
    """
    Test suspend resume for TD guest via Qemu operator
    """
    impl_vm_suspend_resume_qemu(vm_factory, VM_TYPE_TD)


@pytest.mark.bat
def test_efi_suspend_resume_qemu(vm_factory):
    """
    Test suspend resume for EFI guest via Qemu operator
    """
    impl_vm_suspend_resume_qemu(vm_factory, VM_TYPE_EFI)


@pytest.mark.bat
@pytest.mark.nontme
def test_legacy_suspend_resume_qemu(vm_factory):
    """
    Test suspend resume for LEGACY guest via Qemu operator
    """
    impl_vm_suspend_resume_qemu(vm_factory, VM_TYPE_LEGACY)
