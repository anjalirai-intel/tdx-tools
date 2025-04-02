"""
This module provide the case to test the lifecyle for TD/EFI/Legacy guest via
Qemu operator.

"""

import logging
import pytest
from gpl.vmmqmp import VMMQemu
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY, VM_TYPE_EFI, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_qemu_nontd_coexist(vm_factory):
    """
    Test create for legacy guest via Qemu operator
    """
    LOG.info("Create Legacy guest")
    inst_legacy = vm_factory.new_vm(VM_TYPE_LEGACY, vm_class=VMMQemu,
                                    auto_start=True)
    LOG.info("Create EFI guest")
    inst_efi = vm_factory.new_vm(VM_TYPE_EFI, vm_class=VMMQemu,
                                 auto_start=True)
    LOG.info("Create TD guest")
    inst_td = vm_factory.new_vm(VM_TYPE_TD, vm_class=VMMQemu,
                                auto_start=True)

    assert inst_efi.wait_for_ssh_ready()
    assert inst_legacy.wait_for_ssh_ready()
    assert inst_td.wait_for_ssh_ready()


@pytest.mark.regression
def test_qemu_nontd_coexist_qemu_big_model(vm_factory):
    """
    Test create for legacy guest via Qemu operator,
    """
    LOG.info("Create Legacy guest")
    inst_legacy = vm_factory.new_vm(VM_TYPE_LEGACY, vm_class=VMMQemu,
                                    vmspec=VMSpec.model_large(), auto_start=True)
    LOG.info("Create EFI guest")
    inst_efi = vm_factory.new_vm(VM_TYPE_EFI, vm_class=VMMQemu,
                                 vmspec=VMSpec.model_large(), auto_start=True)
    LOG.info("Create TD guest")
    inst_td = vm_factory.new_vm(VM_TYPE_TD, vm_class=VMMQemu,
                                vmspec=VMSpec.model_large(), auto_start=True)

    assert inst_efi.wait_for_ssh_ready()
    assert inst_legacy.wait_for_ssh_ready()
    assert inst_td.wait_for_ssh_ready()


def test_qemu_nontd_coexist_qemu_numa_model(vm_factory):
    """
    Test create for legacy guest via Qemu operator
    """
    LOG.info("Create Legacy guest")
    inst_legacy = vm_factory.new_vm(VM_TYPE_LEGACY, vm_class=VMMQemu,
                                    vmspec=VMSpec.model_numa(), auto_start=True)
    LOG.info("Create EFI guest")
    inst_efi = vm_factory.new_vm(VM_TYPE_EFI, vm_class=VMMQemu,
                                 vmspec=VMSpec.model_numa(), auto_start=True)
    LOG.info("Create TD guest")
    inst_td = vm_factory.new_vm(VM_TYPE_TD, vm_class=VMMQemu,
                                vmspec=VMSpec.model_numa(), auto_start=True)

    assert inst_efi.wait_for_ssh_ready()
    assert inst_legacy.wait_for_ssh_ready()
    assert inst_td.wait_for_ssh_ready()
