"""
This test module tests QEMU Guest Agent file operations within a TDVM, using the QMP commands:

{"execute":"guest-file-open", "arguments":{"path":"/tmp/test_qga_file_ops","mode":"w+"}}
{"execute":"guest-file-write", "arguments":{"handle":1000,"buf-b64":"SGVsbG8gVEQgZ3Vlc3Qh"}}
{"execute":"guest-file-read", "arguments":{"handle":1000}}
{"execute":"guest-file-close", "arguments":{"handle":1000}}

SGVsbG8gVEQgZ3Vlc3Qh is base64 for "Hello TD Guest!".
"""

import logging
import pytest

from pycloudstack.vmparam import VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_tdvm_lifecycle_ga_file_ops(vm_factory):
    """
    Test file operations: Write and read from a file within TD through QEMU Guest Agent

    Step 1: Create TD guest
    Step 2: Send command to QEMU Guest Agent to write to a file within TD guest
    Step 3: Send command to QEMU Guest Agent to read from  a file within TD guest
    """
    test_str = 'SGVsbG8gdGQgZ3Vlc3QhCg=='

    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Write to file")
    r = inst.vmm.qemu_agent_file_write('/tmp/test_qga_file_ops', test_str)
    assert r, 'Fail to write to file'

    LOG.info("Read from file")
    r = inst.vmm.qemu_agent_file_read('/tmp/test_qga_file_ops')
    assert r is not test_str, 'Fail to read from file'
