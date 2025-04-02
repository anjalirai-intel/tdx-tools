"""
BAT testing for multiple TDVM co-exist:

Implemented:
    - Case 1: Test create/destroy multiple TDVMs

TBD:
    - Case 2: Test running same simple workloader in multiple TDVMs
    - Case 3: Test running heavy workloader in multiple TDVMs
    - Case 4: Test the network traffic between multiple TDVMs
"""

import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

MAX_TD_GUEST = 11  # 11 could fit most of RAM/CPU cases


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.bat
def test_tdvms_coexist_create_destroy(vm_factory):
    """
    Test multiple TDVMs create/destory.

    Step 1. Create max number of TDVMs one by one
    Step 2. Destroy each TDVM one by one

    NOTE: vm_factory will cleanup all created VM instance in its __del__ later,
          so do not clean them explicity.
    """
    for index in range(MAX_TD_GUEST):
        LOG.info("Create %d TD", index)
        vm_factory.new_vm(VM_TYPE_TD, auto_start=True)

    for item in vm_factory.vms.values():
        item.wait_for_ssh_ready()
