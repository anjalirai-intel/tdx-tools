"""
This test module provides the basic lifecycle testings for TDVM includes:

- virsh suspend/resume
- virsh start/shutdown
- virsh reboot
"""

import logging
import pytest

from gpl.vmmqmp import VMMQemu
from pycloudstack.vmparam import VM_TYPE_TD, VM_STATE_RUNNING, BOOT_TYPE_GRUB, VM_STATE_SHUTDOWN

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.bat
def test_tdvm_lifecycle_grub_start_shutdown_virsh(vm_factory):
    """
    Test the basic lifecycle: virsh start/virsh shutdown

    Step 1: Create TD guest
    Step 2: Shutdown TD guest and check whether status is shutdown
    Step 3: Start TD guest and check whether status is running
    """

    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True, boot=BOOT_TYPE_GRUB)
    assert inst.wait_for_ssh_ready()

    LOG.info("Shutdown TD guest")
    inst.shutdown()
    ret = inst.wait_for_state(VM_STATE_SHUTDOWN, timeout=30)
    assert ret, "Fail to shutdown instance"

    LOG.info("Start TD guest")
    inst.start()
    ret = inst.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Fail to start instance"


def test_tdvm_lifecycle_grub_start_shutdown_qemu(vm_factory):
    """
    Test the basic lifecycle: virsh start/virsh shutdown

    Step 1: Create TD guest
    Step 2: Shutdown TD guest and check whether status is shutdown
    Step 3: Start TD guest and check whether status is running
    """

    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, vm_class=VMMQemu,
                             auto_start=True, boot=BOOT_TYPE_GRUB)
    assert inst.wait_for_ssh_ready()

    LOG.info("Shutdown TD guest")
    inst.shutdown()
    ret = inst.wait_for_state(VM_STATE_SHUTDOWN)
    assert ret, "Fail to shutdown instance"
