"""
Do tdx attestation test cases, when using grub boot mode
"""
import logging
import pytest
from gpl.vmmqmp import VMMQemu
from pycloudstack.vmparam import VM_TYPE_TD, BOOT_TYPE_GRUB
from td_attest.td_attest_helper import install_packages_for_td_attest, parse_td_report_bin_files, \
    get_td_report_in_vm, append_string_in_kernel_cmdline, restore_kernel_cmdline, \
    copy_out_vmlinuz_from_vm, copy_vmlinuz_into_vm, change_vmlinuz, restore_vmlinuz
from pytdxattest.utility import DEVICE_NODE_NAME_1_5 as DEV_1_5

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

TD_REPORT_FILENAME_IN_VM_DUMMY = "/tmp/td_report_dummy.bin"
TD_REPORT_FILENAME_IN_VM_1 = "/tmp/td_report_f1.bin"
TD_REPORT_FILENAME_IN_VM_2 = "/tmp/td_report_f2.bin"
TD_REPORT_FILENAME_IN_VM_3 = "/tmp/td_report_f3.bin"


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifactory.ini
    pytest.mark.vm_image("latest-guest-image"),            # from artifactory.ini
]


def test_tp_gb_kernel_cmdline(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    1. Start 1 tdx vm with grub boot
    2. Run td-attest to get td-report
    3. Change kernel command line and repeat steps 1-2
    4. Compare TDINFO.RTMR[2] MUST be different
    5, restore kernel command lien.
    6. Compare TDINFO.RTMR[2] MUST be change to the same reture value of step 2
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_GRUB, vm_class=VMMQemu)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_td_attest(vm_inst)

    # change kernel command line to original value
    restore_kernel_cmdline(vm_inst, vm_ssh_key, "test")
    # start tdx vm with grub boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1)

    # change kernel command line
    append_string_in_kernel_cmdline(vm_inst, vm_ssh_key, "test")
    # start tdx vm with grub boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_2)

    # change kernel command line to original value
    restore_kernel_cmdline(vm_inst, vm_ssh_key, "test")
    # start tdx vm with grub boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_3)

    # convert 3 binary file to td report objects
    (td_report_obj_1, td_report_obj_2, td_report_obj_3) = \
        parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1,
                                  TD_REPORT_FILENAME_IN_VM_2, TD_REPORT_FILENAME_IN_VM_3)

    # verify that RTMR[2] is changed with the changing of the kernel command line
    assert td_report_obj_1.td_info.rtmr_2 == td_report_obj_3.td_info.rtmr_2
    assert td_report_obj_1.td_info.rtmr_2 != td_report_obj_2.td_info.rtmr_2


def test_tp_gb_vm_vcpu_num(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    1. Start 1 tdx vm with grub boot
    2. Run td-attest to get td-report
    3. Change number of vcpu and repeat steps 1-2
    4. TDINFO.RTMR[0]s are identical, the number
        of vcpu has no effect
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_GRUB, vm_class=VMMQemu)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_td_attest(vm_inst)

    # start tdx vm with grub boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1)
    vmspec = vm_inst.vmspec

    # change cpu topology, get td report
    LOG.info("test_tp_gb_vm_vcpu_num: vm_inst.update_vmspec")
    vmspec.cores += 1
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_2)

    # change cpu topology to original value, get td report
    LOG.info("test_tp_gb_vm_vcpu_num: vm_inst.update_vmspec")
    vmspec.cores -= 1
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_3)

    # convert 3 binary file to td report objects
    (td_report_obj_1, td_report_obj_2, td_report_obj_3) = \
        parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1,
                                  TD_REPORT_FILENAME_IN_VM_2, TD_REPORT_FILENAME_IN_VM_3)

    # verify that RTMR[0] is changed with the changing of the number of vcpus
    assert td_report_obj_1.td_info.rtmr_0 == td_report_obj_3.td_info.rtmr_0
    assert td_report_obj_1.td_info.rtmr_0 == td_report_obj_2.td_info.rtmr_0


@pytest.mark.regression
def test_tp_gb_vm_memsize(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    1. Start 1 tdx vm with grub boot
    2. Run td-attest to get td-report
    3. Change he memory size and repeat steps 1-2
    4. Compare TDINFO.RTMR[0] MUST be different
    5. Change the memory size to previous value, repeat step 1-2
    6. Compare TDINFO.RTMR[0] MUST be change to the same reture value of step 2
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_GRUB, vm_class=VMMQemu)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_td_attest(vm_inst)

    # start tdx vm with grub boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1)
    vmspec = vm_inst.vmspec

    # change memory size, get td report
    LOG.info("test_tp_gb_vm_memsize: vm_inst.update_vmspec")
    vmspec.memsize = vmspec.memsize * 2
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_2)

    # change memory size to original value, get td report
    LOG.info("test_tp_gb_vm_memsize: vm_inst.orig_vmspec")
    vmspec.memsize = vmspec.memsize / 2
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_3)

    # convert 3 binary file to td report objects
    (td_report_obj_1, td_report_obj_2, td_report_obj_3) = \
        parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1,
                                  TD_REPORT_FILENAME_IN_VM_2, TD_REPORT_FILENAME_IN_VM_3)

    # verify that RTMR[0] is changed with the changing of the memory size
    assert td_report_obj_1.td_info.rtmr_0 == td_report_obj_3.td_info.rtmr_0
    assert td_report_obj_1.td_info.rtmr_0 != td_report_obj_2.td_info.rtmr_0


def test_tp_gb_vmlinuz(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    1. Start 1 tdx vm with grub boot
    2. Run td-attest to get td-report
    3. Change vmlinuz  and repeat steps 1-2
    4. Compare TDINFO.RTMR[2] MUST be different
    """
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, boot=BOOT_TYPE_GRUB, vm_class=VMMQemu)
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    install_packages_for_td_attest(vm_inst)

    # start tdx vm with grub boot, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_1)

    # copy the running vmlinuz from vm to host
    vmlinuz = copy_out_vmlinuz_from_vm(vm_inst, vm_ssh_key, output)
    # change the content of file vmlinuz
    change_vmlinuz(output + "/" + vmlinuz)
    # copy the changed vmlinuz into vm
    copy_vmlinuz_into_vm(vm_inst, output + "/" + vmlinuz)

    # start tdx vm with grub boot, new vmlinuz, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_2)

    # restore the vmlinuz
    restore_vmlinuz(output + "/" + vmlinuz)
    # copy the restored vmlinuz into vm
    copy_vmlinuz_into_vm(vm_inst, output + "/" + vmlinuz)

    # start tdx vm with grub boot, original vmlinuz, get td report
    get_td_report_in_vm(vm_inst, output, vm_ssh_key, TD_REPORT_FILENAME_IN_VM_3)

    # convert 3 binary file to td report objects
    (td_report_obj_1, td_report_obj_2, td_report_obj_3) = \
        parse_td_report_bin_files(output, TD_REPORT_FILENAME_IN_VM_1, TD_REPORT_FILENAME_IN_VM_2,
                                  TD_REPORT_FILENAME_IN_VM_3)

    # verify that RTMR[2] is changed with the changing of vmlinuz
    assert td_report_obj_1.td_info.rtmr_2 == td_report_obj_3.td_info.rtmr_2
    assert td_report_obj_1.td_info.rtmr_2 != td_report_obj_2.td_info.rtmr_2
