"""
Stability testings for multiple TD guests with ramdom choice VMSpec cycling includes:
- virsh create/destroy

"""
import logging
import random
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_STATE_RUNNING, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

MAX_INSTANCE_NUMBER = 10

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.repeat(200)
def test_multi_tdvm_create_destroy(vm_factory):
    """
    Test multiple TD guests create/destory.

    Step 1. Create 10 instances of TD guest with random VMSpec
    Step 2. Destroy each TD guest
    Step 3: repeat step 1 and step 2 by 1000 cycles
    """
    vm_list = []
    model_small = VMSpec(sockets=1, cores=1, threads=1, memsize=4 * 1024 * 1024)
    model_large = VMSpec(sockets=1, cores=4, threads=1, memsize=8 * 1024 * 1024)
    model_numa = VMSpec(sockets=2, cores=2, threads=1, memsize=8 * 1024 * 1024)
    models = [model_small, model_large, model_numa]

    for index in range(MAX_INSTANCE_NUMBER):
        vm_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=random.choice(models), auto_start=True)
        vm_inst.wait_for_state(VM_STATE_RUNNING)
        vm_list.append(vm_inst)

    for index in range(MAX_INSTANCE_NUMBER):
        assert vm_list[index].wait_for_ssh_ready(), "SSH to TD failed"

    for index in range(MAX_INSTANCE_NUMBER):
        vm_list[index].destroy(True)
