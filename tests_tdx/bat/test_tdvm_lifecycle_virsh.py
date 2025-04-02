"""
This test module provides the basic lifecycle testings for TDVM includes:

- virsh suspend/resume
- virsh start/shutdown
- virsh reboot
"""

import logging
import pytest

from pycloudstack.vmparam import VM_STATE_SHUTDOWN, VM_STATE_RUNNING, \
    VM_STATE_PAUSE, VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.mark.smoke
@pytest.mark.bat
def test_tdvm_lifecycle_virsh_suspend_resume(vm_factory):
    """
    Test the basic lifecycle: virsh suspend/virsh resume

    Reference: https://wiki.openstack.org/wiki/Kvm-Pause-Suspend
    User Stories:
    1. User can use "suspend" on annual maintenance day. Instead of terminating
       instances, "suspend" can be used for reducing risks having a problem on
       restarting his system.
    2. instance which is not frequently used can be "suspend". Admins can save
       physical server's resource.
    3. User can use "pause" when they want to get
       backup of instances, and instance is writing data to disks, backup may fails,
       then he may wish instance would stop while backup has been done.

    Step 1: Create TD guest
    Step 2: Suspend TD guest and check whether status is paused
    Step 3: Resume TD guest and check whether status is running
    """

    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Suspend TD guest")
    inst.suspend()
    ret = inst.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    LOG.info("Resume TD guest")
    inst.resume()
    ret = inst.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"


@pytest.mark.smoke
@pytest.mark.bat
def test_tdvm_lifecycle_virsh_start_shutdown(vm_factory):
    """
    Test the basic lifecycle: virsh start/virsh shutdown

    Step 1: Create TD guest
    Step 2: Shutdown TD guest and check whether status is shutdown
    Step 3: Start TD guest and check whether status is running
    """

    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD, auto_start=True)
    inst.wait_for_ssh_ready()

    LOG.info("Shutdown TD guest")
    inst.shutdown()
    ret = inst.wait_for_state(VM_STATE_SHUTDOWN, timeout=30)
    assert ret, "Fail to shutdown instance"

    LOG.info("Start TD guest")
    inst.start()
    ret = inst.wait_for_state(VM_STATE_RUNNING, timeout=30)
    assert ret, "Fail to start instance"
