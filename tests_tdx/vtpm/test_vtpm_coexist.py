"""
This test module check coexist of user TD which has vTPM device, EFI VM and Legacy VM
"""

import logging
import os
import pytest

from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI, VM_TYPE_LEGACY, VMSpec, VM_STATE_RUNNING, VM_STATE_PAUSE

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)


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
def test_vtpm_tdvm_coexist(vm_factory, vm_spec, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Create EFI and Legacy VM - check coexistence
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_vtpm_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vm_spec, has_vtpm=True)

    # create and start VM instance
    td_vtpm_inst.create()
    td_vtpm_inst.start()

    # Check both user TD and vTPM TD are running
    assert td_vtpm_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_vtpm_inst.get_vtpm_td_dom()
    assert td_vtpm_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to check connectivity between user TD and vTPM TD
    cmd = f'tpm2_pcrread'
    LOG.debug(cmd)
    runner = td_vtpm_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    LOG.info("Create TDVM without vTPM device")
    td_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vm_spec, auto_start=True)

    LOG.info("Create a legacy guest")
    legacy_inst = vm_factory.new_vm(VM_TYPE_LEGACY, vmspec=vm_spec, auto_start=True)

    LOG.info("Create a EFI guest")
    efi_inst = vm_factory.new_vm(VM_TYPE_EFI, vmspec=vm_spec, auto_start=True)

    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    assert legacy_inst.wait_for_ssh_ready(), "Could not reach legacy VM"
    assert efi_inst.wait_for_ssh_ready(), "Could not reach EFI VM"

    # Pause all user VMs and resume them
    LOG.info("Suspend TD guest - vtpm")
    td_vtpm_inst.suspend()
    ret = td_vtpm_inst.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    LOG.info("Resume TD guest - vtpm")
    td_vtpm_inst.resume()
    ret = td_vtpm_inst.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"

    LOG.info("Suspend TD guest")
    td_inst.suspend()
    ret = td_inst.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    LOG.info("Resume TD guest")
    td_inst.resume()
    ret = td_inst.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"

    LOG.info("Suspend EFI guest")
    efi_inst.suspend()
    ret = efi_inst.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    LOG.info("Resume EFI guest")
    efi_inst.resume()
    ret = efi_inst.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"

    LOG.info("Suspend Legacy guest")
    legacy_inst.suspend()
    ret = legacy_inst.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    LOG.info("Resume Legacy guest")
    legacy_inst.resume()
    ret = legacy_inst.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"
