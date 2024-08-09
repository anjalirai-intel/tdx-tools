"""
TDX Guest check: to verify TDX guest basic environment:
1. TDX initialized (dmesg)
"""

import datetime
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD
from pycloudstack.vmguest import VirshSSH

__author__ = 'cpio'

# Disable redefined-outer-name since it is false positive for pytest's fixture
# pylint: disable=redefined-outer-name

LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-image"),    # from artifacts.yaml
]


@pytest.fixture(scope="function")
def base_td_guest_inst(vm_factory):
    """
    Create and start a td guest instance
    """
    td_inst = vm_factory.new_vm(VM_TYPE_TD)

    # create and start VM instance
    td_inst.create()
    td_inst.start()

    yield td_inst

    td_inst.destroy()


def test_tdvm_tdx_initialized(base_td_guest_inst):
    """
    check cpu flag "tdx_guest" in TD guest.
    """
    LOG.info("Test if TDX is enabled in TD guest")
    command = "lscpu | grep -i flags"

    qm = VirshSSH(base_td_guest_inst)
    stdout, stderr = qm.check_exec(command)

    LOG.info(stdout)
    qm.close()
    assert "tdx_guest" in stdout, "TDX initilization failed in the guest!"
