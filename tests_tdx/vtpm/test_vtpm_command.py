"""
This test module check tpm2_tools commands on TDVM which has vTPM device
"""

import logging
import os
import pytest

from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import VM_TYPE_TD, VMSpec, VM_STATE_RUNNING

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_vtpm_nvread(vm_factory, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm command tpm2_nvread
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True, auto_start=True)

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to check connectivity between user TD and vTPM TD
    # Encrypt and decrypt some data
    cmd_list = [
        f'tpm2_nvdefine -C o -s 32 -a "ownerread|policywrite|ownerwrite" 1',
        f'echo "please123abc" > nv.dat',
        f'tpm2_nvwrite -C o -i nv.dat 1',
        f'tpm2_nvread -C o -s 12 1'
    ] 
    for cmd in cmd_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    assert runner.stdout[0] == 'please123abc'

def test_vtpm_nvextend(vm_factory, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm command tpm2_extend
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True, auto_start=True)

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to check connectivity between user TD and vTPM TD
    # Encrypt and decrypt some data
    cmd_list = [
        f'tpm2_nvdefine -C o -a "nt=extend|ownerread|policywrite|ownerwrite|writedefine" 1',
        f'echo "my data" | tpm2_nvextend -C o -i- 1',
        f'tpm2_nvread -C o 1 | xxd -p -c32'
    ] 
    for cmd in cmd_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    assert runner.stdout[0] == 'db7472e3fe3309b011ec11565bce4ea6668cc8ecdef7e6fdcda5206687af3f43'

def test_vtpm_unseal(vm_factory, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm command tpm2_unseal
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True, auto_start=True)

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to check connectivity between user TD and vTPM TD
    # Encrypt and decrypt some data
    cmd_list = [
        f'tpm2_createprimary -c primary.ctx -Q',
        f'tpm2_pcrread -Q -o pcr.bin sha256:0,1,2,3',
        f'tpm2_createpolicy -Q --policy-pcr -l sha256:0,1,2,3 -f pcr.bin -L pcr.policy',
        f'echo "secret" > data.dat',
        f'tpm2_create -C primary.ctx -L pcr.policy -i data.dat -u seal.pub -r seal.priv -c seal.ctx -Q',
        f'tpm2_unseal -c seal.ctx -p pcr:sha256:0,1,2,3'
    ] 
    for cmd in cmd_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"
    
    assert runner.stdout[0] == 'secret'

def test_vtpm_load(vm_factory, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm command tpm2_loadexternal
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True, auto_start=True)

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to check connectivity between user TD and vTPM TD
    # Encrypt and decrypt some data
    cmd_list = [
        f'tpm2_createprimary -c primary.ctx',
        f'tpm2_create -C primary.ctx -u pub.dat -r priv.dat',
        f'tpm2_loadexternal -C o -u pub.dat -c pub.ctx'
    ] 
    for cmd in cmd_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

def test_vtpm_pcrread(vm_factory, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm command to read PCR and replay by evnet_logs
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True, auto_start=True)

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Read PCR[0]
    cmd = 'tpm2_pcrread sha256:0 | grep -o "0x.*"'
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"
    pcr0 = runner.stdout[0]

    # Read PCR[0] in event log
    # A simple match is used here just to resolve current output of tpm2_eventlog like this:
    #   ...
    #   pcrs:
    #   sha256:
    #   0  : 0x***
    #   ...
    cmd = 'tpm2_eventlog /sys/kernel/security/tpm0/binary_bios_measurements | grep "^pcrs:" -A2 | grep -o "0x.*"'
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"
    event_log_pcr0 = runner.stdout[0]
    
    # PCR[0] should be replayed by event log
    LOG.debug("PCR[0]: %s", pcr0)
    LOG.debug("PCR[0] in eventlog: %s", event_log_pcr0)
    assert pcr0.lower() == event_log_pcr0.lower(), "Fail to replay PCR[0] in event logs"

def test_vtpm_pcrextend(vm_factory, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm command to extend and read PCR
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True, auto_start=True)

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    cmd = f'tpm2_pcrread sha256:8'
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"
    assert "0x0000000000000000000000000000000000000000000000000000000000000000" in runner.stdout[1]

    # Extend PCR 8 and read PCR
    cmd_list = [
        f'echo "foo" > data',
        f'tpm2_pcrevent 8 data',
        f'tpm2_pcrread sha256:8'
    ] 
    for cmd in cmd_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"    
    
    # New value of PCR[8] should be old one extended with sha256 of "foo"
    assert "0x44F12027AB81DFB6E096018F5A9F19645F988D45529CDED3427159DC0032D921" in runner.stdout[1]

def test_vtpm_quote(vm_factory, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run tpm command to read PCR
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True, auto_start=True)

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Provide and verify quote
    cmd_list = [
        f'tpm2_createek -c 0x81010001 -G rsa -u ekpub.pem -f pem',
        f'tpm2_createak -C 0x81010001 -c ak.ctx -G rsa -s rsassa -g sha256 \
        -u akpub.pem -f pem -n ak.name',
        f'tpm2_quote -c ak.ctx -l sha256:15,16,22 -q abc123 -m quote.msg -s quote.sig -o quote.pcrs -g sha256',
        f'tpm2_checkquote -u akpub.pem -m quote.msg -s quote.sig -f quote.pcrs -g sha256 -q abc123'
    ] 
    for cmd in cmd_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"
