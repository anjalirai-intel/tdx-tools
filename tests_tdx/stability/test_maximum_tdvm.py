"""
Stability testings for multiple TD guests cycling includes:
- virsh create/destroy

"""
import logging
import pytest
import psutil
from pycloudstack import msr
from pycloudstack.vmparam import VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_maximum_tdvm(vm_factory):
    """
    Test maximum TD guests create/destory.

    Step 1. Create maximum instances of TD guests
    Step 2. Destroy each TD guest

    NOTE: vm_factory will cleanup all created VM instance in its __del__ later,
          so do not clean them explicitly.
    """

    # query available key ID number for TD guests
    val = msr.MSR.readmsr(0x87, 63, 32)
    key_number = val - 1
    assert key_number > 0, "no key id is available"
    LOG.debug("key_number: %s", str(key_number))

    # query available host memory
    mem = psutil.virtual_memory()
    mem_slots = mem.free // 2147483648
    assert mem_slots > 0, "no memory is available"
    LOG.debug("mem_slots: %s", str(mem_slots))

    # use the minimum of key ID number and host memory
    max_td_numbers = min(key_number, mem_slots)

    # create TD guest instances up to maximum
    for index in range(max_td_numbers):
        LOG.info("Creating %d TD", index)
        vm_factory.new_vm(VM_TYPE_TD, auto_start=True)

    for item in vm_factory.vms.values():
        item.wait_for_ssh_ready()
