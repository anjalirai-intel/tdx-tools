"""
General help functions for tdx attest test cases
"""
import os
import logging
import time
import pickle

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# The operation `sync` in the guest may need more time to
# save the cache to the persistent storage. Lengthen
# _SYNC_DELAY if the cache can not be saved in time.
_SYNC_DELAY = 30

def install_packages_for_td_attest(vm_inst):
    """
    Install required packages into TDVM,
    1. Copy ../../pytdxattest -> TDVM:/root/
    2. Copy ./vm_td_report_utils.py -> TDVM:/root/pytdxattest
    """
    vm_inst.image.copy_in(os.path.join(os.path.dirname(__file__), "../../tdx-tools/attestation", "pytdxattest"),
                          "/root/")
    vm_inst.image.copy_in(os.path.join(os.path.dirname(__file__), "vm_td_report_utils.py"),
                          "/root/pytdxattest")


def parse_td_report_bin_files(output, *filenames):
    """
    parse a serial of binary files, return the td-report objects
    """
    ret = ()
    for filename in filenames:
        with open(os.path.join(output, os.path.basename(filename)), 'rb') as infile:
            td_report_obj = pickle.load(infile)
            ret += (td_report_obj, )
    for i in ret:
        i.dump()
    return ret


def remote_get_td_report(vm_inst, vm_ssh_key, tr_filename_in_vm, report_data=None):
    """
    Get td-report in TDVM
    1. Run command 'python3 /root/pytdxattest/vm_td_report_utils.py -s <FILENAME> -i <REPORT_DATA>
    which will perform ioctl to get td-report and save it to a file
    2. Run command 'sync' to force all files are sync to disk
    """
    if report_data is not None:
        cmd_to_get_td_report = 'python3 /root/pytdxattest/vm_td_report_utils.py -s %s -i %s'\
            % (tr_filename_in_vm, report_data)
    else:
        cmd_to_get_td_report = 'python3 /root/pytdxattest/vm_td_report_utils.py -s %s'\
            % (tr_filename_in_vm)
    command_list = [
        cmd_to_get_td_report,
        "sync"
    ]
    for cmd in command_list:
        LOG.debug(cmd)
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"


def get_td_report_in_vm(vm_inst, output, vm_ssh_key, filename_in_vm):
    """
    Get td report in vm, save it to binary, and copy it out to host
    """
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready(timeout=1800)

    remote_get_td_report(vm_inst, vm_ssh_key, filename_in_vm, None)

    vm_inst.shutdown()
    vm_inst.destroy()
    time.sleep(5)
    vm_inst.image.copy_out(filename_in_vm, output)


def copy_out_vmlinuz_from_vm(vm_inst, vm_ssh_key, output):
    """
    Copy out the vmlinuz from VM
    1. Run command "uname -r", get the detail kernel name
    2. Copy the file "/boot/vmlinuz-<uname -r>" to the output fold in host
    """
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready(timeout=1800)

    runner = vm_inst.ssh_run("uname -r".split(), vm_ssh_key)
    LOG.info(runner.stdout)

    vm_inst.shutdown()
    vm_inst.destroy()
    time.sleep(5)
    vmlinuz_name = "/boot/vmlinuz-" + runner.stdout[0]
    vm_inst.image.copy_out(vmlinuz_name, output)
    return "vmlinuz-" + runner.stdout[0]


def copy_vmlinuz_into_vm(vm_inst, vmlinuz):
    """
    Copy vmlinuz into VM
    """
    vm_inst.image.copy_in(vmlinuz, "/boot/")


def change_vmlinuz(vmlinuz):
    """
    Change the content of file vmlinuz
    Modify the string in the mbr of vmlinuz to simulate the behavior of vmlinuz being tampered.
    This does not affect the function of vmlinux, but it will affect the measurment value of
    vmlinuz.
    1. Read the first 512 Bytes of vmlinuz
    2. Replace the string "disk" to "DISK"
    3. Save it to file vmlinuz
    """
    with open(vmlinuz, "r+b") as file_vmlinuz:
        mbr = file_vmlinuz.read(512)
        changed_mbr = mbr.replace(b"disk", b"DISK")
        file_vmlinuz.seek(0)
        file_vmlinuz.write(changed_mbr)


def restore_vmlinuz(vmlinuz):
    """
    Reverse the operation of function "change_vmlinuz"
    1. Read the first 512 Bytes of vmlinuz
    2. Replace the string "DISK" to "disk"
    3. Save it to file vmlinuz
    """
    with open(vmlinuz, "r+b") as file_vmlinuz:
        mbr = file_vmlinuz.read(512)
        changed_mbr = mbr.replace(b"DISK", b"disk")
        file_vmlinuz.seek(0)
        file_vmlinuz.write(changed_mbr)


def append_string_in_kernel_cmdline(vm_inst, vm_ssh_key, append_string):
    '''
    Append string in kernel command line
    For example:
        "linux   /boot/vmlinuz-5.14.0-36.el8.x86_64+spr root=/dev/vda3 rw console=hvc0" ->
        "linux   /boot/vmlinuz-5.14.0-36.el8.x86_64+spr root=/dev/vda3 rw console=hvc0 test"
    1. Start VM
    2. In file /boot/efi/EFI/centos/grub.cfg, append string to line "linux ...."
    '''
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready(timeout=1800)
    command = "grubby --update-kernel=/boot/vmlinuz-$(uname -r) --args=\"%s\"" % (append_string)
    vm_inst.ssh_run(command.split(), vm_ssh_key)
    command = "sync"
    vm_inst.ssh_run(command.split(), vm_ssh_key)
    time.sleep(_SYNC_DELAY)
    vm_inst.shutdown()
    vm_inst.destroy()
    time.sleep(5)


def restore_kernel_cmdline(vm_inst, vm_ssh_key, append_string):
    """
    Restore kernel command line
    For example:
        "linux   /boot/vmlinuz-5.14.0-36.el8.x86_64+spr root=/dev/vda3 rw console=hvc0 test" ->
        "linux   /boot/vmlinuz-5.14.0-36.el8.x86_64+spr root=/dev/vda3 rw console=hvc0"
    1. Start VM
    2. In file /boot/efi/EFI/centos/grub.cfg, delte the string from line "linux ...."
    """
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready(timeout=1800)
    command = "grubby --update-kernel=/boot/vmlinuz-$(uname -r) --remove-args=\"%s\"" % (append_string)
    vm_inst.ssh_run(command.split(), vm_ssh_key)
    command = "sync"
    vm_inst.ssh_run(command.split(), vm_ssh_key)
    time.sleep(_SYNC_DELAY)
    vm_inst.shutdown()
    vm_inst.destroy()
    time.sleep(5)


def install_packages_for_td_rtmr(vm_inst):
    """
    Install required packages into TDVM,
    1. Copy ../../pytdxattest -> TDVM:/root/
    2. Copy ./vm_td_rtmr_utils.py -> TDVM:/root/pytdxattest
    3. Copy ./vm_td_report_utils.py -> TDVM:/root/pytdxattest
    """
    vm_inst.image.copy_in(os.path.join(os.path.dirname(__file__), "../../tdx-tools/attestation", "pytdxattest"),
                          "/root/")
    vm_inst.image.copy_in(os.path.join(os.path.dirname(__file__), "vm_td_rtmr_utils.py"),
                          "/root/pytdxattest")
    vm_inst.image.copy_in(os.path.join(os.path.dirname(__file__), "vm_td_report_utils.py"),
                          "/root/pytdxattest")


def ssh_and_extend_rtmr(vm_inst, vm_ssh_key, extend_data, extended_rtmr_register, output_file):
    """
    Extend rtmr register in TD guest instance

    1. Run command 'python3 /root/pytdxattest/vm_td_rtmr_utils.py -e <EXTEND_DATA> \
        -r <EXTENDED_RTMR_REGISTER> -f <RTMR_EXTEND_OUTPUT_FILE>' which will perform \
        ioctl to extend the specific rtmr register with certain data.\
        Extend result will be documented in the output file
    """

    cmd_to_extend_rtmr = 'python3 /root/pytdxattest/vm_td_rtmr_utils.py -e %s -r %d -f %s'\
        % (extend_data, extended_rtmr_register, output_file)
    runner = vm_inst.ssh_run(cmd_to_extend_rtmr.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.ssh_run("sync", vm_ssh_key)


def shutdown_and_destroy_td(vm_inst):
    """
    Shutdown and destroy td
    """
    vm_inst.shutdown()
    vm_inst.destroy()
    time.sleep(5)


def check_rtmr_extend_result(vm_inst, output_file, output):
    """
    Copy rtmr extend result out to local
    """
    vm_inst.image.copy_out(output_file, output)
    with open(os.path.join(output, os.path.basename(output_file)), 'rb') as infile:
        rtmr_extend_result = pickle.load(infile)

    return rtmr_extend_result


def extend_and_check_rtmr(vm_inst, vm_ssh_key, extend_data, extended_rtmr_register, output_file, output):
    """
    Extend rtmr register and get extend result
    """
    ssh_and_extend_rtmr(vm_inst, vm_ssh_key, extend_data, extended_rtmr_register, output_file)
    shutdown_and_destroy_td(vm_inst)
    res = check_rtmr_extend_result(vm_inst, output_file, output)

    return res

def install_packages_for_ima(vm_inst):
    """
    Install required packages into TDVM,
    1. Copy ../../pytdxattest -> TDVM:/root/
    2. Copy ./vm_td_ccel_utils.py -> TDVM:/root/pytdxattest
    2. Copy ./vm_td_report_utils.py -> TDVM:/root/pytdxattest
    """
    vm_inst.image.copy_in(os.path.join(os.path.dirname(__file__), "../../tdx-tools/attestation", "pytdxattest"),
                          "/root/")
    vm_inst.image.copy_in(os.path.join(os.path.dirname(__file__), "vm_td_ccel_utils.py"),
                          "/root/pytdxattest")
    vm_inst.image.copy_in(os.path.join(os.path.dirname(__file__), "vm_td_report_utils.py"),
                          "/root/pytdxattest")

def remote_get_ccel_data(vm_inst, vm_ssh_key, ccel_output_file, td_report_output_file):
    """
    1. Run command 'python3 /root/pytdxattest/vm_td_ccel_utils.py -c <CCEL_OUTPUT_FILE> -r <TD_REPORT_OUTPUT_FILE>'\
            which will fetch CCEL data, replay RTMR values and put them in the CCEL output file. Also, it will\
            fetch TD report and put it inside the TD report output file.
    """
    cmd_to_fetch_ccel_data = 'python3 /root/pytdxattest/vm_td_ccel_utils.py -c %s -r %s'\
        % (ccel_output_file, td_report_output_file)
    runner = vm_inst.ssh_run(cmd_to_fetch_ccel_data.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.ssh_run("sync", vm_ssh_key)
