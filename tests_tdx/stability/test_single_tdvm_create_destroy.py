"""
Stability testings for single TDVM cycling includes:

- virsh create/destroy
"""
import logging
import pytest
from pycloudstack.vmguest import VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_name("stability-single-td-centos8"),
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.repeat(2000)
def test_single_tdvm_cycle_create_destroy(vm_factory):
    """
    Test the basic lifecycle: virsh create/virsh destroy

    Step 1: Create TD guest
    Step 2: Destroy TD guest
    Step 3: repeat step 1 and step 2 by 500 cycles for Alpha
    DPMO <= 2000
       1 defects / ( 1 TD guest * 500 cycles ) * 1000000 = 2000 DPMO

    """

    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True)
    inst.wait_for_ssh_ready()
    inst.destroy(delete_image=True, delete_log=True)
