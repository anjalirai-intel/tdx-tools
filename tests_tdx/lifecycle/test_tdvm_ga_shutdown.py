"""
This test module tests QEMU Guest Agent QMP command to shutdown a TDVM:
{"execute":"guest-shutdown"}
"""

import logging
import pytest
from libvirt import libvirtError, VIR_ERR_AGENT_UNRESPONSIVE

from pycloudstack.vmparam import VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.regression
def test_tdvm_lifecycle_ga_shutdown(vm_factory):
    """
    Test shutting down a TD guest using QEMU Guest Agent command

    Step 1: Create TD guest
    Step 2: Send command to QEMU Guest agent to shutdown the TD guest
    """

    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Request QEMU Guest Agent to shutdown the TD guest")
    # QEMU Guest Agent shuts the TD guest down abruptly, checking
    # for VM state does not work.
    try:
        inst.vmm.qemu_agent_shutdown()
    except libvirtError as e:
        LOG.info(e)
        assert e.get_error_code() == VIR_ERR_AGENT_UNRESPONSIVE, "QEMU Guest Agent shutdown fail"
