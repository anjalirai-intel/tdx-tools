"""
This test module check lifecycle of user TD which has vTPM device
"""

import logging
import os
import pytest
import libvirt
import time

from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import VM_TYPE_TD, VMSpec, VM_STATE_SHUTDOWN, VM_STATE_RUNNING, VM_STATE_PAUSE

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)
VIRT_CONN = libvirt.open("qemu:///system")

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

vm_spec_list = [
    VMSpec(sockets=1, cores=1, memsize=2*1024*1024),
    VMSpec(sockets=1, cores=1, memsize=4*1024*1024),
    VMSpec(sockets=2, cores=2, memsize=16*1024*1024),
    VMSpec(sockets=1, cores=8, memsize=32*1024*1024),
]

@pytest.mark.parametrize("vm_spec", vm_spec_list)
def test_tdvm_vtpm_create_destroy(vm_factory, vm_spec, vm_ssh_pubkey, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm2_tools checking communication between vTPM TD and user TD
    3. Destroy TDVM - vTPM TD and user TD should be deleted
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vm_spec, has_vtpm=True)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "tpm2_encrypt.sh"), "/opt/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to check connectivity between user TD and vTPM TD
    # Encrypt and decrypt some data
    cmd = f'/opt/tpm2_encrypt.sh -d "Secret Data"'
    LOG.debug(cmd)
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # Destroy user TD, vTPM TD should be deleted as well
    td_inst.destroy()

    vtpm_dom_new = None
    try:
        vtpm_dom_new = VIRT_CONN.lookupByUUIDString(vtpm_id)
    except libvirt.libvirtError:
        LOG.info("Cannot find vtpm TD domain with ID %s", vtpm_id)
    
    assert vtpm_dom_new == None, "vTPM TD is not deleted as expected!"

@pytest.mark.parametrize("vm_spec", vm_spec_list)
def test_tdvm_define_undefine(vm_factory, vm_spec, vm_ssh_pubkey, vm_ssh_key):
    """
    1. Define TDVM with vTPM device - vTPM TD is running. user TD is shutdown.
    2. Start user TD - both vTPM TD and user TD are running
    3. Run tpm2_tools checking communication between vTPM TD and user TD
    4. Destroy TDVM - user TD is shutdown and vTPM TD is running
    5. Start TDVM, repeat step 2-3
    6. Undefine TDVM - both user TD and vTPM TD are deleted 
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vm_spec, has_vtpm=True)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "tpm2_encrypt.sh"), "/opt/")

    # create VM instance
    td_inst.create()

    # Check vTPM TD is running
    time.sleep(3)
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"
    
    # Start user TD and check it's running
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Fail to ssh TD"

    # Run tpm command to check connectivity between user TD and vTPM TD
    # Encrypt and decrypt some data
    cmd = f'/opt/tpm2_encrypt.sh -d "Secret Data"'
    LOG.debug(cmd)
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # Destroy user TD but not undefine it
    LOG.info("Destroy user TD, but not Undefine it")
    td_inst.destroy(is_undefined=False)
    assert td_inst.wait_for_state(VM_STATE_SHUTDOWN), "user TD should be destroyed but NOT undefined"
    
    # Check vTPM TD is still running
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"
    LOG.debug("vtpm TD is in %s state", td_inst.vtpm_state())

    # Start user TD again
    LOG.info("Start user TD again")
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Fail to ssh TD"
    LOG.debug("user TD is in %s state", td_inst.state())

    # Run tpm command to check connectivity between user TD and vTPM TD
    # Encrypt and decrypt some data
    cmd = f'/opt/tpm2_encrypt.sh -d "Secret Data"'
    LOG.debug(cmd)
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # Destroy and undefine user TD - both user TD and vTPM TD will be deleted
    LOG.info("Destroy and undefine user TD")
    td_inst.destroy()

    vtpm_dom_new = None
    try:
        vtpm_dom_new = VIRT_CONN.lookupByUUIDString(vtpm_id)
    except libvirt.libvirtError:
        LOG.info("Cannot find vtpm TD domain with ID %s", vtpm_id)
    
    assert vtpm_dom_new == None, "vTPM TD is not deleted as expected!"

@pytest.mark.parametrize("vm_spec", vm_spec_list)
def test_tdvm_suspend_resume(vm_factory, vm_spec, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD are running. 
    2. Run tpm2_tools generate RSA key in TPM device
    3. Suspend TDVM - user TD is paused and vTPM TD is running
    4. Resume TDVM - user TD and vTPM TD are running
    5. Retrieve RSA key from TPM device
    """
    
    LOG.info("Create TDVM with vTPM device")

    # create and start TDVM instance
    td_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vm_spec, has_vtpm=True, auto_start=True)
    assert td_inst.wait_for_ssh_ready(), "Fail to ssh TD"

    # Check vTPM TD is running
    time.sleep(3)
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING

    # Run tpm command to create RSA key pair in TPM
    cmd_list = [
        "tpm2_createprimary -c primary_01.ctx",
        "tpm2_create -C primary_01.ctx -Gaes128 -u key_01.pub -r key_01.priv"
    ]
    
    for cmd in cmd_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    # Suspend user TD
    LOG.info("Suspend TD guest")
    td_inst.suspend()
    ret = td_inst.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"
    
    # Check vTPM TD is still running
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Resume user TD
    LOG.info("Resume TD guest")
    td_inst.resume()
    ret = td_inst.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"

    # Load the object created above to make sure vTPM TD still works
    cmd = f'tpm2_load -C primary_01.ctx -u key_01.pub -r key_01.priv -c key_01.ctx'
    LOG.debug(cmd)
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

def test_vtpm_suspend_resume(vm_factory, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD are running. 
    2. Run tpm2_tools generate RSA key in TPM device
    3. Suspend vTPM TD - user TD is running and vTPM TD is paused
    4. Resume vTPM TD - user TD and vTPM TD are running
    5. Retrieve RSA key from TPM device
    """
    
    LOG.info("Create TDVM with vTPM device")

    # create and start TDVM instance
    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True, auto_start=True)
    assert td_inst.wait_for_ssh_ready(), "Fail to ssh TD"

    # Check vTPM TD is running
    time.sleep(3)
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to create RSA key pair in TPM
    cmd_list = [
        "tpm2_createprimary -c primary_01.ctx",
        "tpm2_create -C primary_01.ctx -Gaes128 -u key_01.pub -r key_01.priv"
    ]
    
    for cmd in cmd_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    # Suspend vTPM TD
    LOG.info("Suspend vTPM TD")
    vtpm_dom.suspend()
    time.sleep(3)
    assert td_inst.vtpm_state() == VM_STATE_PAUSE, "vTPM TD is not paused"
    
    # Check user TD is still running
    assert td_inst.state() == VM_STATE_RUNNING, "user TD is not running"

    # Resume vTPM TD
    LOG.info("Resume vTPM TD")
    vtpm_dom.resume()
    time.sleep(3)
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Load the object created above to make sure vTPM TD still works
    cmd = f'tpm2_load -C primary_01.ctx -u key_01.pub -r key_01.priv -c key_01.ctx'
    LOG.debug(cmd)
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"
