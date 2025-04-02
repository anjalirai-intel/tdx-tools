"""
Do tdx attestation test cases
"""
import os
import logging
import time
import cpuid
import pickle
import pytest
from td_attest_helper import install_packages_for_td_attest, remote_get_td_report
from pycloudstack.vmparam import VM_TYPE_TD, BOOT_TYPE_GRUB
from pytdxattest.utility import DEVICE_NODE_NAME_1_5 as DEV_1_5

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

TD_REPORT_DATA_FOR_TEST = "1234567890" * 6 + "1234"

TD_REPORT_FILENAME_IN_VM_1 = "/tmp/td_report_f1.bin"
TD_REPORT_FILENAME_IN_VM_2 = "/tmp/td_report_f2.bin"

NOF_THREADS_FOR_CONCURRENT_TEST = 10

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifactory.ini
    pytest.mark.vm_image("latest-guest-image"),            # from artifactory.ini
]


def _create_vm(vm_factory, vm_ssh_pubkey):
    """
    Create TDVM with 'grub' boot mode
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_GRUB)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    return vm_inst


def _start_vm(vm_inst):
    """
    Start TDVM
    """
    install_packages_for_td_attest(vm_inst)
    vm_inst.create()
    vm_inst.start()
    return None


def _remote_mp_get_td_report(vm_inst, vm_ssh_key, tr_filename_in_vm, nof_threads, report_data=None):
    """
    Get td-report in TDVM, using multi threads to execute it concurrently
    1. Run command 'python3 /root/pytdxattest/vm_td_report_utils.py -m <NOF_THREADS> <FILENAME> -i <REPORT_DATA>
    which will create multiple threads to perform ioctl to get td-report concurrently, and save them to files
    2. Run command 'sync' to force all files are sync to disk
    """
    if report_data is not None:
        cmd_to_get_td_report = 'python3 /root/pytdxattest/vm_td_report_utils.py -m %d %s -i %s'\
            % (nof_threads, tr_filename_in_vm, report_data)
    else:
        cmd_to_get_td_report = 'python3 /root/pytdxattest/vm_td_report_utils.py -m %d %s'\
            % (nof_threads, tr_filename_in_vm)
    command_list = [
        cmd_to_get_td_report,
        "sync"
    ]
    for cmd in command_list:
        LOG.debug(cmd)
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"


def _start_vm_and_get_td_report_file(vm_factory, vm_ssh_pubkey, vm_ssh_key, output,
                                     filename_in_vm=TD_REPORT_FILENAME_IN_VM_1,
                                     report_data=None):
    """
    Get td-report in TDVM, save the result, copy it from TDVM to host, and parse it to a td report object
    """
    if report_data is not None:
        assert len(report_data) == 64

    vm_inst = _create_vm(vm_factory, vm_ssh_pubkey)
    _start_vm(vm_inst)
    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"
    remote_get_td_report(vm_inst, vm_ssh_key, filename_in_vm, report_data)
    time.sleep(5)
    vm_inst.destroy()
    vm_inst.image.copy_out(filename_in_vm, output)

    with open(os.path.join(output, os.path.basename(filename_in_vm)), 'rb') as infile:
        td_report_obj = pickle.load(infile)

    return td_report_obj


def _start_vm_and_mp_get_td_report_file(vm_factory, vm_ssh_pubkey, vm_ssh_key, output,
                                        filename_in_vm=TD_REPORT_FILENAME_IN_VM_1,
                                        report_data=None):
    """
    Get td-report in TDVM, using multi threads to execute it concurrently, save the results,
    copy then from TDVM to host, and parse them to a td report object list
    """
    vm_inst = _create_vm(vm_factory, vm_ssh_pubkey)
    _start_vm(vm_inst)
    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"
    _remote_mp_get_td_report(vm_inst, vm_ssh_key, filename_in_vm, NOF_THREADS_FOR_CONCURRENT_TEST,
                             report_data)
    time.sleep(5)
    vm_inst.destroy()
    for i in range(NOF_THREADS_FOR_CONCURRENT_TEST):
        vm_inst.image.copy_out("%s-%d" % (filename_in_vm, i), output)

    td_report_obj_list = []
    for i in range(NOF_THREADS_FOR_CONCURRENT_TEST):
        with open(os.path.join(output, os.path.basename("%s-%d" % (filename_in_vm, i))), 'rb') \
                as infile:
            td_report_obj = pickle.load(infile)
        td_report_obj_list.append(td_report_obj)

    return td_report_obj_list


@pytest.fixture(scope="module")
def td_report_obj_default(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    A td-report object, generated with default report date
    """
    return _start_vm_and_get_td_report_file(vm_factory, vm_ssh_pubkey, vm_ssh_key, output)


@pytest.fixture(scope="module")
def td_report_obj_with_special_data(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    A td-report object, generated with special report date
    """
    return _start_vm_and_get_td_report_file(vm_factory, vm_ssh_pubkey, vm_ssh_key, output,
                                            filename_in_vm=TD_REPORT_FILENAME_IN_VM_2,
                                            report_data=TD_REPORT_DATA_FOR_TEST)


@pytest.fixture(scope="module")
def td_report_mp_obj_default(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    A td-report object list, generated with default report date
    """
    return _start_vm_and_mp_get_td_report_file(vm_factory, vm_ssh_pubkey, vm_ssh_key, output)


@pytest.fixture(scope="module")
def td_report_mp_obj_with_special_data(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    A td-report object list, generated with special report date
    """
    return _start_vm_and_mp_get_td_report_file(vm_factory, vm_ssh_pubkey, vm_ssh_key, output,
                                               filename_in_vm=TD_REPORT_FILENAME_IN_VM_2,
                                               report_data=TD_REPORT_DATA_FOR_TEST)


@pytest.fixture(scope="module")
def td_report_obj_from_multi_vms(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    A td-report ojbect list, generated with default and special report date, get from 2 TDVMs
    """
    td_report_obj_list = []
    basename = TD_REPORT_FILENAME_IN_VM_1.split(".")[0]
    suffix_name = TD_REPORT_FILENAME_IN_VM_1.split(".")[1]
    for i in range(2):
        filename = basename + "-" + str(i) + "." + suffix_name
        td_report_obj = _start_vm_and_get_td_report_file(vm_factory, vm_ssh_pubkey, vm_ssh_key,
                                                         output, filename_in_vm=filename)
        td_report_obj_list.append(td_report_obj)
    return td_report_obj_list


def test_tr_single_vm(td_report_obj_default):
    """
    Purpose: Validate TDVM can generate td-report correctly
    1. Start 1 tdx vm
    2. get td-report
    3. Check the content of output, make sure that the content must not all are '0'
    """
    LOG.info("test_tr_single_vm")
    assert td_report_obj_default.data != '\x00' * 0x400


def test_tr_check_tcb_info_valid(td_report_obj_default):
    """
    Check data field TD_REPORT.TEE_TCB_INFO.VALID. must be 'ff 01 00 00 00 00 00 00'
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check the value must be 'ff 01 00 00 00 00 00 00' in tdx 1.0 or
        'ff 01 03 00 00 00 00 00' in early tdx 1.5

    Ref: Intel® CPU Architectural Extensions Specification
        in https://www.intel.com/content/www/us/en/developer/articles/technical/intel-trust-domain-extensions.html
    """
    VALID_VAL = td_report_obj_default.device_node.get_tee_tcb_info_valid_val()
    assert td_report_obj_default.tee_tcb_info.valid == VALID_VAL


def test_tr_check_tcb_info_tee_tcb_svn(td_report_obj_default):
    """
    Check data field TD_REPORT.TEE_TCB_INFO.TEE_TCB_SVN
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check the value, make sure that the content must not all are '0'
    """
    module_version = td_report_obj_default.tee_tcb_info.module_version
    svn_bytes = td_report_obj_default.tee_tcb_info.tee_tcb_svn
    LOG.info(f'module version: {module_version}'
             f'derived from svn bytes: {svn_bytes}'
            )
    assert module_version != None


@pytest.mark.regression
def test_tr_check_tcb_info_mrsignerseam(td_report_obj_default):
    """
    Check the data field TD_REPORT.TEE_TCB_INFO.MRSIGNERSEAM
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check the value are all '0'
    """
    assert td_report_obj_default.tee_tcb_info.mrsignerseam == b"\x00" * 0x30


def test_tr_check_tcb_info_attributes(td_report_obj_default):
    """
    Check the data field TD_REPORT.TEE_TCB_INFO.ATTRIBUTES
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check the value are all '0'
    """
    assert td_report_obj_default.tee_tcb_info.attributes == \
        b"\x00\x00\x00\x00\x00\x00\x00\x00"


def test_tr_check_tdinfo_attributes(td_report_obj_default):
    """
    Check the data field TD_REPORT.TD_INFO.ATTRIBUTES
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check the values are all '0' except PKS and PERFMON fields
    """
    td_report_obj_default.dump()
    attr = td_report_obj_default.td_info.attributes
    # clean bit 0 to skip DEBUG field
    attr[0] = attr[0] & 0b11111110

    if td_report_obj_default.device_node.device_node_name == DEV_1_5:
        # clear bit 28 to skip SEPT_VE_DISABLE field
        # TODO: need confirm by the spec
        attr[3] = attr[3] & 0b11101111
        # clear bit 29 to skip MIGRATABLE field
        attr[3] = attr[3] & 0b11011111

    # clear bit 30 to skip PKS field
    attr[3] = attr[3] & 0b10111111
    # clear bit 63 to skip PERFMON field controlled by pmu=on/off
    attr[7] = attr[7] & 0b01111111
    assert attr == b"\x00\x00\x00\x00\x00\x00\x00\x00"

def test_tr_check_tdinfo_xfam(td_report_obj_default):
    """
    Check the data field TD_REPORT.TD_INFO.XFAM
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. AVX CPUID(0xD,0x0).EAX[2]
       AVX512 CPUID(0xD,0x0).EAX[7:5]
       AMX CPUID(0xD,0x0).EAX[18:17]
       CET CPUID(0xD,0x1).ECX[12:11]
    """
    avx_amx = cpuid.cpuid_count(leaf=0xd, subleaf=0x0)[0]
    cet = cpuid.cpuid_count(leaf=0xd, subleaf=0x1)[2] & 0x1800
    xfam = bytearray(8)
    xfam[0] = avx_amx & 0xff
    xfam[1] = avx_amx >> 8 & 0xff | cet >> 8
    xfam[2] = avx_amx >> 16 & 0xff
    assert td_report_obj_default.td_info.xfam == xfam


def test_tr_check_mac_report_type(td_report_obj_default):
    """
    Check the data field TD_REPORT.REPORTMACSTRUCT.REPORTTYPE
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check the value is '81 00 00 00 00 00 00 00'
    """
    assert td_report_obj_default.report_mac_struct.report_type == \
        b"\x81\x00\x00\x00\x00\x00\x00\x00"


def test_tr_check_mac_cpusvn(td_report_obj_default):
    """
    Check the td-report field TD_REPORT.REPORTMACSTRUCT.CPUSVN
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check the value, make sure that the content must not all are '0'
    """
    assert td_report_obj_default.report_mac_struct.cpusvn != \
        b"\x00" * 0x10


def test_tp_reserved_region(td_report_obj_default):
    """
    Check the td-report field, all reserved region.
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check check the reserverd region, MUST all are '0'
    """
    RESERVE_LEN_IN_TEE_TCB_INFO = 0x6f
    if td_report_obj_default.device_node.device_node_name == DEV_1_5:
        RESERVE_LEN_IN_TEE_TCB_INFO = 0x5f
    assert td_report_obj_default.report_mac_struct.reserverd1 == b"\x00" * 8
    assert td_report_obj_default.report_mac_struct.reserverd2 == b"\x00" * 0x20
    assert td_report_obj_default.tee_tcb_info.reserved == b"\x00" * RESERVE_LEN_IN_TEE_TCB_INFO
    assert td_report_obj_default.reserved == b"\x00" * 0x11


def test_tp_check_appdata(td_report_obj_with_special_data):
    """
    Check the td-report field TD_REPORT.REPORTMACSTRUCT.REPORTDATA
    1. Start 1 tdx vm
    2. Run tdx measure tool to get td-report
    3. Check the filed REPORTMACSTRUCT.REPORTDATA is same with the value generated by tdx measure
    tool
    """
    assert td_report_obj_with_special_data.report_mac_struct.report_data == \
        TD_REPORT_DATA_FOR_TEST.encode()


@pytest.mark.regression
def test_tp_check_mac(td_report_obj_with_special_data, td_report_obj_default):
    """
    Check the td-report field TD_REPORT.REPORTMACSTRUCT.MAC
    1. Start  2 tdx vms
    2. Run tdx measure tool to get td-report twice
    3.  Check the values got from 2 TDVMs are different
    """
    assert td_report_obj_with_special_data.report_mac_struct.mac != \
        td_report_obj_default.report_mac_struct.mac


def test_tr_multi_vms(td_report_obj_from_multi_vms):
    """
    Validate TDVM can correctly generate td-report, and the td-report generated by different TDVM are same
    1. Start 2 tdx vms, same vm configuration
    2. get td-report
    3. Check the content of output, make sure that the content is not all are '0'
    4. Compare the td report got from 2 VMs, make sure the data fields are same
    """
    td_report_obj_A = td_report_obj_from_multi_vms[0]
    td_report_obj_B = td_report_obj_from_multi_vms[1]
    assert td_report_obj_A.data == td_report_obj_B.data


@pytest.mark.regression
def test_tp_gb_check_grub2_packages(td_report_obj_default):
    """
    Validate the measureable grub2 are used
    1. Start 1 tdx vm with grub boot
    2. Run tdx measure tool to get td-report
    3. Check TDREPORT.TDINFO.RTMR[2], must not all are '0'
    """
    assert td_report_obj_default.td_info.rtmr_0 != '\x00' * 0x30


@pytest.mark.regression
def test_tr_concurrent_single_vm(td_report_mp_obj_default):
    """
    Call Ioctrl concurrent in single TDVM
    1. Start 1 tdx vm
    2. Create 10  threads, and call ioctl in every threads
    3. Compare the td-reports are same
    """
    for i in range(len(td_report_mp_obj_default) - 1):
        assert td_report_mp_obj_default[0].data == td_report_mp_obj_default[i].data


@pytest.mark.regression
def test_tr_concurrent_multi_vms(td_report_mp_obj_default, td_report_mp_obj_with_special_data):
    """
    Call Ioctrl concurrent in multiple TDVMs
    1. Start 2 tdx vms
    2. Create 10 threads per vm, and call ioctl in every threads
    3. Compare the td-reports
    """
    for i in range(len(td_report_mp_obj_default) - 1):
        assert td_report_mp_obj_default[0].data == td_report_mp_obj_default[i].data
    for i in range(len(td_report_mp_obj_with_special_data) - 1):
        assert td_report_mp_obj_with_special_data[0].data == \
            td_report_mp_obj_with_special_data[i].data
