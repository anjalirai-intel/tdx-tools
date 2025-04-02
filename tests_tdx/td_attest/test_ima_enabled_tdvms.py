"""
IMA testing for TDVM:

Implemented:
    - Case 1: Test create/destroy VM (either TDVM or EFI VM) with RTMR based IMA enabled (with all built-in policies)
    - Case 2: Test RTMR verifying in TDVM with RTMR based IMA enabled (with all built-in policies)
    - Case 3: Test RTMR verifying failure in TDVM with RTMR based IMA enabled as 'tcb'
"""

import base64
import logging
import os
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI, KernelCmdline
from td_attest.td_attest_helper import install_packages_for_ima, parse_td_report_bin_files,\
        remote_get_td_report, remote_get_ccel_data
import time

__author__ = 'cpio'
LOG = logging.getLogger(__name__)

TD_REPORT_FILENAME_IN_VM_1 = "/tmp/td_report_f1.bin"
CCEL_FILENAME_IN_VM_1 = "/tmp/ccel_data.bin"

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

pytest_input = [
    (VM_TYPE_TD, ""),
    (VM_TYPE_TD, "critical_data"),
    #(VM_TYPE_TD, "secure_boot"),
    (VM_TYPE_TD, "tcb"),
    (VM_TYPE_TD, "fail_securely"),
    (VM_TYPE_EFI, ""),
    (VM_TYPE_EFI, "critical_data"),
    #(VM_TYPE_EFI, "secure_boot"),
    (VM_TYPE_EFI, "tcb"),
    (VM_TYPE_EFI, "fail_securely")
]

def catch_rtmr_values_from_event_log(output, filename):
    """
    Fetch RTMR values that replayed from event log
    """
    infile = open(os.path.join(output, os.path.basename(filename)), 'rb')
    ccel_rtmr_0 = infile.readline().strip().decode('utf-8')
    ccel_rtmr_1 = infile.readline().strip().decode('utf-8')
    ccel_rtmr_2 = infile.readline().strip().decode('utf-8')
    ccel_rtmr_3 = infile.readline().strip().decode('utf-8')
    infile.close()

    return ccel_rtmr_0, ccel_rtmr_1, ccel_rtmr_2, ccel_rtmr_3

@pytest.mark.bat
@pytest.mark.parametrize("vm_type, ima_policy", pytest_input)
def test_vms_with_ima_enabled(vm_factory, vm_type, ima_policy):
    """
    Test VM boot up with RTMR based IMA enabled.

    Step 1. Create VM with type set by vm_type
    Step 2. Create TDVM with IMA params set by ima_policy
    Step 3. Destroy TDVM

    NOTE: vm_factory will cleanup all created VM instance in its __del__ later,
          so do not clean them explicity.
    """
    cmdline = KernelCmdline()

    LOG.info("Create VM with IMA (RTMR based) enabled, using vm type %s and ima_policy set to '%s'", vm_type, ima_policy)
    cmdline.add_field_from_string("ima_hash=sha384")
    if ima_policy != "":
        cmdline.add_field_from_string("ima_policy="+ima_policy)
    td_inst = vm_factory.new_vm(vm_type, cmdline=cmdline, auto_start=True)
    assert td_inst.wait_for_ssh_ready(), "Could not reach TD VM"

@pytest.mark.bat
@pytest.mark.parametrize("vm_type, ima_policy", pytest_input)
def test_rtmr_verification_with_ima_enabled(vm_factory, vm_ssh_pubkey, vm_ssh_key, output, vm_type, ima_policy):
    """
    Test RTMR verify after enabling IMA in TDVM with critical data

    Step 1. Create TDVM with IMA param enabled
    Step 2. Fetch TD report and CCEL event logs from TDVM in a single operation
    Step 3. Verify RTMR value with event logs
    Step 4. Destroy TDVM
    """
    if (vm_type == VM_TYPE_EFI):
        return
    cmdline = KernelCmdline()

    LOG.info("Create TDVM with IMA policy set to '%s'", ima_policy)
    cmdline.add_field_from_string("ima_hash=sha384")
    cmdline.add_field_from_string("ima_policy="+ima_policy)
    td_inst = vm_factory.new_vm(VM_TYPE_TD, cmdline=cmdline)
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_ima(td_inst)

    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(timeout=300), "Could not reach TD VM"

    remote_get_ccel_data(td_inst, vm_ssh_key, CCEL_FILENAME_IN_VM_1, TD_REPORT_FILENAME_IN_VM_1)

    td_inst.shutdown()
    td_inst.destroy()
    time.sleep(5)
    td_inst.image.copy_out(TD_REPORT_FILENAME_IN_VM_1, output)
    td_inst.image.copy_out(CCEL_FILENAME_IN_VM_1, output)

    td_report_obj = parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1)
    (ccel_rtmr_0, ccel_rtmr_1, ccel_rtmr_2, ccel_rtmr_3) = \
        catch_rtmr_values_from_event_log(output, CCEL_FILENAME_IN_VM_1)

    assert base64.b64encode(bytearray(td_report_obj[0].td_info.rtmr_0)).decode("utf-8") == ccel_rtmr_0,\
        "Verify RTMR[0] failed."
    assert base64.b64encode(bytearray(td_report_obj[0].td_info.rtmr_1)).decode("utf-8") == ccel_rtmr_1,\
        "Verify RTMR[1] failed."
    assert base64.b64encode(bytearray(td_report_obj[0].td_info.rtmr_2)).decode("utf-8") == ccel_rtmr_2,\
        "Verify RTMR[2] failed."
    assert base64.b64encode(bytearray(td_report_obj[0].td_info.rtmr_3)).decode("utf-8") == ccel_rtmr_3,\
        "Verify RTMR[3] failed."

@pytest.mark.bat
def test_rtmr_verification_failure_with_ima_enabled_tcb(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    Test RTMR verify after enabling IMA in TDVM with critical data

    Step 1. Create TDVM with IMA param enabled
    Step 2. Fetch TD report and CCEL event logs from TDVM using two operations
    Step 3. Verify RTMR value with event logs, since the fetch TD report operation shall introduce\
            one extra event log by IMA. Verification for RTMR[2] will fail.
    Step 4. Destroy TDVM
    """
    cmdline = KernelCmdline()

    LOG.info("Create TDVM with IMA policy set to 'tcb'")
    cmdline.add_field_from_string("ima_hash=sha384")
    cmdline.add_field_from_string("ima_policy=tcb")
    td_inst = vm_factory.new_vm(VM_TYPE_TD, cmdline=cmdline)
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_ima(td_inst)

    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(timeout=300), "Could not reach TD VM"

    remote_get_td_report(td_inst, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1, None)
    remote_get_ccel_data(td_inst, vm_ssh_key, CCEL_FILENAME_IN_VM_1, None)

    td_inst.shutdown()
    td_inst.destroy()
    time.sleep(5)
    td_inst.image.copy_out(TD_REPORT_FILENAME_IN_VM_1, output)
    td_inst.image.copy_out(CCEL_FILENAME_IN_VM_1, output)

    td_report_obj = parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1)
    (ccel_rtmr_0, ccel_rtmr_1, ccel_rtmr_2, ccel_rtmr_3) = \
        catch_rtmr_values_from_event_log(output, CCEL_FILENAME_IN_VM_1)

    assert base64.b64encode(bytearray(td_report_obj[0].td_info.rtmr_0)).decode("utf-8") == ccel_rtmr_0,\
        "Verify RTMR[0] failed."
    assert base64.b64encode(bytearray(td_report_obj[0].td_info.rtmr_1)).decode("utf-8") == ccel_rtmr_1,\
        "Verify RTMR[1] failed."
    assert base64.b64encode(bytearray(td_report_obj[0].td_info.rtmr_3)).decode("utf-8") == ccel_rtmr_3,\
        "Verify RTMR[3] failed."
    assert base64.b64encode(bytearray(td_report_obj[0].td_info.rtmr_2)).decode("utf-8") != ccel_rtmr_2,\
        "Verify RTMR[2] error."
