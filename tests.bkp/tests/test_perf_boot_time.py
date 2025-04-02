"""
This module provide the case to test VM boot with max vCPU

"""

import logging
import psutil
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_STATE_RUNNING, VM_TYPE_EFI, VM_TYPE_TD, VMSpec
from pycloudstack.util import timeit
from pycloudstack.vmguest import VirshSSH

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]
# Remving VMSpec.model_migtd() as it is consistently failing to get IP address.
# Commenting the test out until we find a solution to the the IP address issue.
@pytest.mark.parametrize("vm_type", [VM_TYPE_TD, VM_TYPE_EFI, VM_TYPE_LEGACY])
@pytest.mark.parametrize("vmspec", [VMSpec.model_large(), VMSpec.model_base(), VMSpec.model_numa()])
def test_boot_time(vm_factory, vm_type, vmspec):
    """
    Test boot TD guest with max vcpu KVM supports
    """

    LOG.info("Create guest")
    inst = vm_factory.new_vm(vm_type, vmspec)
    # customize the VM image
    inst.create()

    def boot_vm_and_wait_ssh():
        inst.start()
        VirshSSH(inst)
    
    timeit(boot_vm_and_wait_ssh)()
    # Destroy VM to release CPU resource
    inst.destroy()

