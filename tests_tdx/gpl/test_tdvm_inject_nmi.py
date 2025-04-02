"""
This module provide the case to verify inject NMI to TD guest
"""

import logging
import pytest
from gpl.vmmqmp import VMMQemu
from pycloudstack.vmparam import VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.fixture(scope="function")
def base_td_guest_inst(vm_factory):
    """
    Create and start a td guest instance
    """
    td_inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True, vm_class=VMMQemu)
    td_inst.wait_for_ssh_ready()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    yield td_inst

    td_inst.destroy()


def test_tdvm_inject_nmi(base_td_guest_inst):
    """
    Test injecting an NMI to a TD guest
    """
    LOG.info("Test injecting NMI to TD guest")

    # on success inject_nmi returns an empty dict
    assert not base_td_guest_inst.vmm.inject_nmi()['return']
