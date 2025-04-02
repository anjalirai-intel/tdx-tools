"""
Stability testings for multiple TD guests cycling includes:
- virsh create/destroy
Create a TD guest with 128 vCPU and destroy it. Repeat 200 cycles.

"""
import logging
import pytest
from pycloudstack.vmparam import VM_STATE_RUNNING, VM_TYPE_TD, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

vmspec = VMSpec(sockets=2, cores=64, threads=1, memsize=64 * 1024 * 1024)


@pytest.mark.repeat(200)
def test_tdvm_create_destroy_large(vm_factory):
    """
    Test multiple TD guests create/destory.

    Step 1. Create a TD guest with 128 vCPU
    Step 2. Destroy the TD guest
    Step 3. repeat step 1 and step 2 by 200 cycles
    """

    # create and start VM instance
    LOG.info("Create TD guest")
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vmspec, auto_start=True)
    assert vm_inst.wait_for_state(VM_STATE_RUNNING), "TD guest fail to boot"
    assert vm_inst.wait_for_ssh_ready(), "TD guest fail to ssh"

    # destroy vm
    vm_inst.destroy()
