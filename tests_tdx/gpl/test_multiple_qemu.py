"""
This module provide the case to test the lifecyle for TD/EFI/Legacy guest via
Qemu operator.

"""

import logging
import threading
import pytest
from gpl.vmmqmp import VMMQemu
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY, VM_TYPE_EFI

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

MAX_INSTANCE_NUMBER = 11


def vm_thread_func(vm_factory, vm_instance_type):
    """
    Common VM creatation thread function.
    """
    inst = vm_factory.new_vm(vm_instance_type, vm_class=VMMQemu,
                             auto_start=True)
    inst.wait_for_ssh_ready()


@pytest.mark.regression
def test_qemu_multiple_td_concurrent(vm_factory):
    """
    Test suspend resume for legacy guest via Qemu operator
    """
    vm_thread_list = []
    for _ in range(MAX_INSTANCE_NUMBER):
        tinst = threading.Thread(target=vm_thread_func,
                                 args=(vm_factory, VM_TYPE_TD))
        tinst.start()
        vm_thread_list.append(tinst)

    for item in vm_thread_list:
        item.join()


def test_qemu_multiple_legacy_concurrent(vm_factory):
    """
    Test suspend resume for legacy guest via Qemu operator
    """
    vm_thread_list = []
    for _ in range(MAX_INSTANCE_NUMBER):
        tinst = threading.Thread(target=vm_thread_func,
                                 args=(vm_factory, VM_TYPE_LEGACY))
        tinst.start()
        vm_thread_list.append(tinst)

    for item in vm_thread_list:
        item.join()


def test_qemu_multiple_efi_concurrent(vm_factory):
    """
    Test suspend resume for legacy guest via Qemu operator
    """
    vm_thread_list = []
    for _ in range(MAX_INSTANCE_NUMBER):
        tinst = threading.Thread(target=vm_thread_func,
                                 args=(vm_factory, VM_TYPE_EFI))
        tinst.start()
        vm_thread_list.append(tinst)

    for item in vm_thread_list:
        item.join()
