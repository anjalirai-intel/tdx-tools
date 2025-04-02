"""
This test module check lifecycle of multiple user TDs which has vTPM device
"""

import logging
import os
import pytest
import libvirt

from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import VM_TYPE_TD, VMSpec, VM_STATE_SHUTDOWN, VM_STATE_RUNNING, VM_STATE_PAUSE

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)
VIRT_CONN = libvirt.open("qemu:///system")
MAX_GUEST_NUM = 2

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_tdvm_multi_create_destroy(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    1. Create multiple TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm2_tools checking communication between vTPM TD and user TD
    3. Destroy TDVM - vTPM TD and user TD should be deleted
    """
    
    LOG.info("Create TDVM with vTPM device")

    # Record userr TD instance and vtpm TD UUID
    vtpm_dict = {}

    for i in range(MAX_GUEST_NUM):
        td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True)
        td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
        td_inst.image.copy_in(
            os.path.join(CURR_DIR, "tpm2_encrypt.sh"), "/opt/")

        td_inst.create()
        td_inst.start()

    # Check both user TD and vTPM TD are running
    for td_inst in vm_factory.vms.values():
        assert td_inst.wait_for_ssh_ready(), "TDVM ssh is not ready"
        vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
        assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"
        vtpm_dict[td_inst] = [vtpm_dom, vtpm_id]

    # Run tpm command to check connectivity between user TD and vTPM TD
    cmd = f'tpm2_pcrread'
    LOG.debug(cmd)
    for td_inst in vm_factory.vms.values():
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    # Destroy user TD, vTPM TD should be deleted as well
    for td_inst in vm_factory.vms.values():
        td_inst.destroy()
        vtpm_dom_new = None
        try:
            vtpm_dom_new = VIRT_CONN.lookupByUUIDString(vtpm_dict[td_inst][1])
        except libvirt.libvirtError:
            LOG.info("Cannot find vtpm TD domain with ID %s", vtpm_dict[td_inst][1])    
        assert vtpm_dom_new == None, "vTPM TD is not deleted as expected!"

def test_tdvm_multi_suspend_resume(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    1. Create multiple TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm2_tools checking communication between vTPM TD and user TD
    3. Suspend TDVM - vTPM TD is still running 
    4. Resume TDVM and run tpm2_tools checking communication between vTPM TD and user TD
    """
    
    LOG.info("Create TDVM with vTPM device")

    # Record userr TD instance and vtpm TD UUID
    vtpm_dict = {}

    for i in range(MAX_GUEST_NUM):
        td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True)
        td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
        td_inst.image.copy_in(
            os.path.join(CURR_DIR, "tpm2_encrypt.sh"), "/opt/")

        td_inst.create()
        td_inst.start()

    # Check both user TD and vTPM TD are running
    for td_inst in vm_factory.vms.values():
        assert td_inst.wait_for_ssh_ready(), "TDVM ssh is not ready"
        vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
        assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"
        vtpm_dict[td_inst] = [vtpm_dom, vtpm_id]

    # Run tpm command to check connectivity between user TD and vTPM TD
    cmd = f'tpm2_pcrread'
    LOG.debug(cmd)
    for td_inst in vm_factory.vms.values():
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    # Suspend user TD, vTPM TD should be running
    for td_inst in vm_factory.vms.values():
        td_inst.suspend()
        assert td_inst.wait_for_state(VM_STATE_PAUSE), "TDVM should be suspended"
        assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"
    
    # Resume user TD - both vTPM TD and TDVM should be running
    for td_inst in vm_factory.vms.values():
        td_inst.resume()
        assert td_inst.wait_for_state(VM_STATE_RUNNING), "TDVM should be running"
        assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"  
        cmd = f'tpm2_pcrread'
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"
