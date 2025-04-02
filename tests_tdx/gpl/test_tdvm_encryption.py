"""
This module provide the case to verify
  1. non-TD is not encrypted (memeory is the same as origional kernel file)
  2. TD is encrypted (memeory differs from origional kernel file)
"""

import os
import re
import logging
from datetime import datetime
import pytest
from gpl.vmmqmp import VMMQemu
from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import KernelCmdline
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


# NUM_LINES_TO_COMPARE: the max lines of instructions to compare
#
# Please be very CAREFUL to enlarge the value
# Since sometimes objdump and qemu monitor command *x* give different disassemble result
#
# For example, for the instruction "f7 05 88 4f bf 01 01",
#
# objdump disassemble result:
#      ffffffff8100005e: f7 05 88 4f bf 01 01     testl  $0x1,0x1bf4f88(%rip)
#      ffffffff81000065: 00 00 00
#
# qemu monitor command *x* disassemble result:
#      ffffffff8100005e: f7 05 88 4f bf 01 01 00  testl  $1, 0x1bf4f88(%rip)
#      ffffffff81000066: 00 00
NUM_LINES_TO_COMPARE = 20


def _read_from_kernel_file(kernel_file):
    """
    Reads the instructions from the kernel file, from the beginning of .text section

    Steps to do that:
    1. extract the kernel image using extract-vmlinux tool
    2. disassemble the kernel image using objdump
    3. extract .text address from the dissambled kernel
    3. read NUM_LINES_TO_COMPARE lines from the dissambled kernel

    Note:
    1. step 1 & 2 are in the helper script verify_tdvm_encryption/disassemble_kernel.sh
       since both steps need output redirection which is not well supported by NativeCmdRunner
    """
    tmp_dis_kfile = "/tmp/kernel-{}.dis".format(datetime.now().strftime("%m%d%Y%H%M%S"))
    this_dir = os.path.dirname(os.path.realpath(__file__))
    script_file = f"{this_dir}/verify_tdvm_encryption/disassemble_kernel.sh"
    runner = NativeCmdRunner(["/bin/bash", script_file, tmp_dis_kfile, kernel_file])
    runner.runwait()
    assert runner.retcode == 0

    text_addr = None
    instructions = []
    with open(tmp_dis_kfile, "r") as f_dis:
        while len(instructions) < NUM_LINES_TO_COMPARE:
            line = f_dis.readline()
            if line is None:
                break
            if text_addr is None:
                if line.find("<.text>") >= 0:
                    text_addr = line[0:16]
            else:
                instructions.append(line.strip())

    os.remove(tmp_dis_kfile)

    assert text_addr is not None
    assert len(instructions) == NUM_LINES_TO_COMPARE
    return text_addr, instructions


def _read_from_vm(vmfactory, vm_type, address):
    """
    Reads the instructions form virtual machine memory.
    Both td, efi, legacy virtual machines are supported, determined by *vm_type*.
    It reads start from the *address*, and the lenght to read is hardcoded 0x40

    Steps:
    1. pause the virtual machine
    2. read memory via qemu monitor command *x*

    Note:
    1. step 2 is in the helper script verify_tdvm_encryption/read_vm_mem.sh
       since both steps need output redirection which is not well supported by NativeCmdRunner
    2. "nokaslr" must be appended to the kernal command line to disable kaslr
    3. the virtual machine must be of class vmex.VMMQemu since qemu monitor is used
    """
    fmt = "/20i"
    addr = f"0x{address}"
    cmdline = KernelCmdline()
    cmdline.add_field_from_string("nokaslr")
    vm_inst = vmfactory.new_vm(vm_type, vm_class=VMMQemu, auto_start=True, cmdline=cmdline)
    assert vm_inst.wait_for_ssh_ready(), "Could not reach TD"
    vm_inst.suspend()

    this_dir = os.path.dirname(os.path.realpath(__file__))
    script_file = f"{this_dir}/verify_tdvm_encryption/read_vm_mem.sh"
    # Assert vm_inst.vmm is an instance of VMMQemu, and directly access its property monitor_port
    runner = NativeCmdRunner(["/bin/bash", script_file, str(vm_inst.vmm.monitor_port), fmt, addr])
    runner.runwait()
    assert runner.retcode == 0
    memory = runner.stdout
    vm_inst.destroy()
    return memory


def _formalize_string(line):
    """
    Formalize the instruction lines since the lines from objdump and qemu monitor command differ
    """
    line = re.sub(":(\\s*)", " ", line)
    line = re.sub("0x", "", line)
    return line


def _compare_memory(mem1, mem2):
    """
    Compare the group of memory (from kernel image file / running virtual machine)
    In fact what are being compared are not original binary blobs of the read memory,
    but the disassembled instruction starting from .text sections,
    read via either _read_from_kernel_file or _read_from_vm
    """
    num_lines = min(len(mem1), len(mem2))

    for iline in range(num_lines):
        words1 = _formalize_string(mem1[iline]).split(" ")
        words2 = _formalize_string(mem2[iline]).split(" ")

        # Only compare the leading 2 words: address and the 1st byte of the instruction
        if words1[0] != words2[0] or words1[1] != words2[1]:
            LOG.info("Memory compare: differs (\"%s %s\" - \"%s %s\")",
                     words1[0], words1[1], words2[0], words2[1])
            return False

    LOG.info("Memory compare: unique")
    return True


def _dump_lines(lines, name):
    LOG.debug("Read instruction from %s:", name)
    for line in lines:
        LOG.debug("    %s", line)


@pytest.mark.bat
def test_tdvm_encryption(vm_factory, vm_kernel):
    """
    Verify memory is encrypted in TD guest

    1. Read memory:
       a. extract / disassemble kernel file
       b. read memory from non-TD via qemu monitor
       c. read memory from TD via qemu monitor
    2. Comparation:
       a. test memory of kernel file & non-TD, should be unique
       b. test memory of kernel file & TD, should differ
    """
    address, lines_file = _read_from_kernel_file(vm_kernel)
    _dump_lines(lines_file, "kernel file")

    lines_efi = _read_from_vm(vm_factory, VM_TYPE_EFI, address)

    lines_td = _read_from_vm(vm_factory, VM_TYPE_TD, address)

    LOG.info("Comparining memory: kernel fils - non-TD")
    assert _compare_memory(lines_file, lines_efi)

    LOG.info("Comparining memory: kernel fils - TD")
    assert not _compare_memory(lines_file, lines_td)
