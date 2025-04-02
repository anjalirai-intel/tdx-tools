"""
This file includes multiple tests for RTMR write in direct boot mode

Implemented:
    - Case 1: Test extend RTMR with valid data
    - Case 2: Test extend RTMR with data with invalid length
    - Case 3: Test extend RTMR with invalid RTMR register number
    - Case 4: Test extend RTMR with invalid privilege \
        (register index 0/1 cannot be extended in userspace)
    - Case 5: Test same extend data written to multiple TDs

"""

import logging
import datetime
import pytest

from pycloudstack.vmparam import VM_TYPE_TD
from td_attest_helper import install_packages_for_td_rtmr, parse_td_report_bin_files,\
    remote_get_td_report, extend_and_check_rtmr, ssh_and_extend_rtmr,\
    shutdown_and_destroy_td, check_rtmr_extend_result

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

VALID_DIGEST_LENGTH = 48
INVALID_DIGEST_LENGTH = 50

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
RTMR_TEST_EXTEND_VALUE = '1'
DEFAULT_RTMR_REGISTER = 2
INVALID_RTMR_REGISTER = 4
RTMR_REGISTER_WITH_INVALID_PRIVILEGE = 1

EXTEND_SUCCESS = 'RTMR_EXTEND_SUCCESS'
EXTEND_FAILURE = 'RTMR_EXTEND_FAILURE'
EXTEND_FAILURE_WITH_WRONG_INPUT = 'RTMR_EXTEND_FAILURE_WITH_WRONG_INPUT'


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.fixture(scope="function")
def base_td_guest_inst(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Create base td guest for each test
    """
    base_td_inst = _create_and_start_td_inst(vm_factory, vm_ssh_pubkey, vm_ssh_key)

    yield base_td_inst


def _create_and_start_td_inst(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Create and start a td guest instance
    """
    td_inst = vm_factory.new_vm(VM_TYPE_TD)
    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # install packages needed for rtmr extend
    install_packages_for_td_rtmr(td_inst)
    # create and start VM instance
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    # activate td_guest fd in the guest TD
    LOG.info("activating td_guest fd in the guest")
    cmd_to_activate_td_device = 'echo 1 > /sys/devices/platform/tdx_guest/authorized'
    runner = td_inst.ssh_run(cmd_to_activate_td_device.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    return td_inst


def test_rtmr_write_success(base_td_guest_inst, vm_ssh_key, output):
    """
    Test RTMR write with valid digest

    Test Steps
    ----------
    1. ssh into TD guest and extend rtmr with valid digest
    2. assert extend result with success
    """
    LOG.info("Write RTMR register with valid data")
    digest = RTMR_TEST_EXTEND_VALUE * VALID_DIGEST_LENGTH
    output_file = f"/tmp/tdx_rtmr_extend_result_check_{DATE_SUFFIX}.log"
    result = extend_and_check_rtmr(
            base_td_guest_inst, vm_ssh_key, digest, int(DEFAULT_RTMR_REGISTER), output_file, output)
    assert result == EXTEND_SUCCESS


def test_rtmr_write_with_wrong_length(base_td_guest_inst, vm_ssh_key, output):
    """
    Test RTMR write with wrong length

    Test Steps
    ----------
    1. ssh into TD guest and extend rtmr with wrong length digest
    2. assert extend result with failure
    """
    LOG.info("Write RTMR register with invalid data")
    digest = RTMR_TEST_EXTEND_VALUE * INVALID_DIGEST_LENGTH
    output_file = f"/tmp/tdx_rtmr_extend_result_check_{DATE_SUFFIX}.log"
    result = extend_and_check_rtmr(
            base_td_guest_inst, vm_ssh_key, digest, int(DEFAULT_RTMR_REGISTER), output_file, output)
    assert result == EXTEND_FAILURE_WITH_WRONG_INPUT


def test_rtmr_write_with_invalid_register(base_td_guest_inst, vm_ssh_key, output):
    """
    Test RTMR write with invalid register number

    Test Steps
    ----------
    1. ssh into TD guest and extend rtmr with invalid register number
    2. assert extend result with failure
    """
    LOG.info("Write to RTMR invalid register")
    digest = RTMR_TEST_EXTEND_VALUE * VALID_DIGEST_LENGTH
    output_file = f"/tmp/tdx_rtmr_extend_result_check_{DATE_SUFFIX}.log"
    result = extend_and_check_rtmr(
            base_td_guest_inst, vm_ssh_key, digest, int(INVALID_RTMR_REGISTER), output_file, output)
    assert result == EXTEND_FAILURE


def test_rtmr_write_with_invalid_privilege(base_td_guest_inst, vm_ssh_key, output):
    """
    Test RTMR write with invalid privilege

    Test Steps
    ----------
    1. ssh into TD guest and extend rtmr with register that cannot be modified in user-space
    2. assert extend result with failure
    """
    LOG.info("Write to RTMR register with invalid privilege")
    digest = RTMR_TEST_EXTEND_VALUE * VALID_DIGEST_LENGTH
    output_file = f"/tmp/tdx_rtmr_extend_result_check_{DATE_SUFFIX}.log"
    result = extend_and_check_rtmr(base_td_guest_inst, vm_ssh_key, digest,
                                int(RTMR_REGISTER_WITH_INVALID_PRIVILEGE), output_file, output)
    assert result == EXTEND_FAILURE


def test_rtmr_write_on_multiple_td(vm_factory, vm_ssh_pubkey, base_td_guest_inst, vm_ssh_key, output):
    """
    Test RTMR write on multiple TDs and check if the results are equal

    Test Steps
    ----------
    1. create extra compared TD guest
    1. ssh into TD guest A and B to extend rtmr[2] with same value
    2. assert extend result with success
    3. get value of rtmr[2] from each TD guest report and assert if the result are equal
    """
    LOG.info("Write to rtmr in multiple TDs with same extend data \
            and check if the extend result are equal")
    digest = RTMR_TEST_EXTEND_VALUE * VALID_DIGEST_LENGTH
    compared_td_inst = _create_and_start_td_inst(vm_factory, vm_ssh_pubkey, vm_ssh_key)

    # extend rtmr
    output_file1 = f"/tmp/tdx_rtmr_extend_result_check_A_{DATE_SUFFIX}.log"
    output_file2 = f"/tmp/tdx_rtmr_extend_result_check_B_{DATE_SUFFIX}.log"
    ssh_and_extend_rtmr(
            base_td_guest_inst, vm_ssh_key, digest, DEFAULT_RTMR_REGISTER, output_file1)
    ssh_and_extend_rtmr(
            compared_td_inst, vm_ssh_key, digest, DEFAULT_RTMR_REGISTER, output_file2)

    # do get tdreport
    output_fileA = "/tmp/td_report_f1.bin"
    output_fileB = "/tmp/td_report_f2.bin"
    remote_get_td_report(base_td_guest_inst, vm_ssh_key, output_fileA, report_data=None)
    remote_get_td_report(compared_td_inst, vm_ssh_key, output_fileB, report_data=None)

    shutdown_and_destroy_td(base_td_guest_inst)
    shutdown_and_destroy_td(compared_td_inst)

    # check rtmr extend result
    result = check_rtmr_extend_result(base_td_guest_inst, output_file1, output)
    result_compared = check_rtmr_extend_result(compared_td_inst, output_file2, output)

    assert result == EXTEND_SUCCESS
    assert result_compared == EXTEND_SUCCESS

    # verify td report
    base_td_guest_inst.image.copy_out(output_fileA, output)
    compared_td_inst.image.copy_out(output_fileB, output)

    (td_report_obj_1, td_report_obj_2) = \
        parse_td_report_bin_files(output, output_fileA, output_fileB)


    assert td_report_obj_1.td_info.rtmr_2 == td_report_obj_2.td_info.rtmr_2
