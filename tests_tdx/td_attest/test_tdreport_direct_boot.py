"""
Do tdx attestation test cases, when using direct boot mode
"""
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, BOOT_TYPE_DIRECT
from pycloudstack.vmparam import KernelCmdline
from gpl.vmmqmp import VMMQemu
from td_attest.td_attest_helper import install_packages_for_td_attest, parse_td_report_bin_files, \
    get_td_report_in_vm, copy_out_vmlinuz_from_vm, change_vmlinuz
from pytdxattest.utility import DEVICE_NODE_NAME_1_5 as DEV_1_5

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

TD_REPORT_FILENAME_IN_VM_1 = "/tmp/td_report_f1.bin"
TD_REPORT_FILENAME_IN_VM_2 = "/tmp/td_report_f2.bin"
TD_REPORT_FILENAME_IN_VM_3 = "/tmp/td_report_f3.bin"


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifactory.ini
    pytest.mark.vm_image("latest-guest-image"),            # from artifactory.ini
]


def test_tp_db_kernel_cmdline(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    In direct mode, after changed the kernel command line, RTMR[1] value will change
    1. Start 1 tdx vm with direct boot.
    2. Run td-attest to get td-report.
    3. Change kernel command line and repeat steps 1-2.
    4. TDINFO.RTMR[1]s are identical, TDINFO.RTMR[2]s are different.
    5. restore kernel command line.
    6. TDINFO.RTMR[1] and TDINFO.RTMR[2]s are the same to reture value 
       of step 2 repsectively.
    
    Note:
    1. In direct boot, RTMR[1] measures the kernel by TDVF.
    2. In direct boot, RTMR[2] measures the kernel cmdline and initrd by kernel
       efistub.
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_DIRECT, vm_class=VMMQemu)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_td_attest(vm_inst)
    
    # start tdx vm with direct boot, get td report
    orig_cmdline = vm_inst.cmdline
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1)

    # change kernel command line, get td report
    changed_cmdline = KernelCmdline(str(orig_cmdline) + " nokaslr")
    vm_inst.update_kernel_cmdline(changed_cmdline)
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_2)

    # restore kernel command line to original value
    vm_inst.update_kernel_cmdline(orig_cmdline)
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_3)

    # convert 3 binary file to td report objects
    (td_report_obj_1, td_report_obj_2, td_report_obj_3) = \
        parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1,
                                  TD_REPORT_FILENAME_IN_VM_2, TD_REPORT_FILENAME_IN_VM_3)

    # verify that RTMR[1] has the same value.
    assert td_report_obj_1.td_info.rtmr_1 == td_report_obj_3.td_info.rtmr_1
    assert td_report_obj_1.td_info.rtmr_1 == td_report_obj_2.td_info.rtmr_1
    # verify that RTMR[2] varies.
    assert td_report_obj_1.td_info.rtmr_2 == td_report_obj_3.td_info.rtmr_2
    assert td_report_obj_1.td_info.rtmr_2 != td_report_obj_2.td_info.rtmr_2


@pytest.mark.regression
def test_tp_db_vm_vcpu_num(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    1. Start 1 tdx vm with direct boot
    2. Run td-attest to get td-report
    3. Change number of vcpu and repeat steps 1-2
    4. TDINFO.RTMR[0]s are identical, the number
        of vcpu has no effect
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_DIRECT, vm_class=VMMQemu)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_td_attest(vm_inst)

    # start tdx vm with direct boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1)
    vmspec = vm_inst.vmspec

    # change cpu topology, get td report
    LOG.info("test_tp_db_vm_vcpu_num: vm_inst.update_vmspec")
    vmspec.cores += 1
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_2)

    # change cpu topology to original value, get td report
    LOG.info("test_tp_db_vm_vcpu_num: vm_inst.update_vmspec")
    vmspec.cores -= 1
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_3)

    # convert 3 binary file to td report objects
    (td_report_obj_1, td_report_obj_2, td_report_obj_3) = \
        parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1,
                                  TD_REPORT_FILENAME_IN_VM_2, TD_REPORT_FILENAME_IN_VM_3)

    # verify that RTMR[0] is changed with the changing of the number of vcpus
    assert td_report_obj_1.td_info.rtmr_0 == td_report_obj_3.td_info.rtmr_0
    assert td_report_obj_1.td_info.rtmr_0 == td_report_obj_2.td_info.rtmr_0

def test_tp_db_vm_memsize(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    1. Start 1 tdx vm with direct boot
    2. Run td-attest to get td-report
    3. Change he memory size and repeat steps 1-2
    4. Compare TDINFO.RTMR[0] MUST be different
    5. Change the memory size to previous value, repeat step 1-2
    6. Compare TDINFO.RTMR[0] MUST be changed to the same return value of step 1
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_DIRECT, vm_class=VMMQemu)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_td_attest(vm_inst)

    # start tdx vm with direct boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1)
    vmspec = vm_inst.vmspec

    # change memory size, get td report
    LOG.info("test_tp_db_vm_memsize: vm_inst.update_vmspec")
    vmspec.memsize = vmspec.memsize * 2
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_2)

    # change memory size to original value, get td report
    LOG.info("test_tp_db_vm_memsize: vm_inst.update_vmspec")
    vmspec.memsize = vmspec.memsize / 2
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_3)

    # convert 3 binary file to td report objects
    (td_report_obj_1, td_report_obj_2, td_report_obj_3) = \
        parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1,
                                  TD_REPORT_FILENAME_IN_VM_2, TD_REPORT_FILENAME_IN_VM_3)

    # verify that RTMR[0] is changed with the changing of the memory size
    assert td_report_obj_1.td_info.rtmr_0 == td_report_obj_3.td_info.rtmr_0
    assert td_report_obj_1.td_info.rtmr_0 != td_report_obj_2.td_info.rtmr_0


def test_tp_db_vmlinuz(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    1. Start 1 tdx vm with direct boot
    2. Run td-attest to get td-report
    3. Change vmlinuz  and repeat steps 1-2
    4. Compare TDINFO.RTMR[1] MUST be different
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_DIRECT, vm_class=VMMQemu)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_td_attest(vm_inst)

    # copy the running vmlinuz from vm to host
    vmlinuz = copy_out_vmlinuz_from_vm(vm_inst, vm_ssh_key, output)
    # change the content of file vmlinuz
    change_vmlinuz(output + "/" + vmlinuz)

    # start tdx vm with direct boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1)

    orig_kernel = vm_inst.kernel

    # start tdx vm with direct boot, new vmlinuz, get td report
    LOG.info("test_tp_db_vmlinuz: vm_inst.update_kernel")
    vm_inst.update_kernel(output + "/" + vmlinuz)
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_2)

    # start tdx vm with direct boot, original vmlinuz, get td report
    LOG.info("test_tp_db_vmlinuz: vm_inst.update_kernel to original kernel")
    vm_inst.update_kernel(orig_kernel)
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_3)

    # convert 3 binary file to td report objects
    (td_report_obj_1, td_report_obj_2, td_report_obj_3) = \
        parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1, TD_REPORT_FILENAME_IN_VM_2,
                                  TD_REPORT_FILENAME_IN_VM_3)

    # verify that RTMR[1] is changed with the changing of vmlinuz
    assert td_report_obj_1.td_info.rtmr_1 == td_report_obj_3.td_info.rtmr_1
    assert td_report_obj_1.td_info.rtmr_1 != td_report_obj_2.td_info.rtmr_1
