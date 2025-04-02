"""
TDX Guest check: TSX (Transactional Synchronization Extensions) should be configurable
"""
import logging
import pytest
from environment.conf_utils import get_td_vm
from environment.conf_utils import get_cpuid_info
from environment.conf_utils import get_msr_info


__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),    # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-image"),      # from artifacts.yaml
]


def get_cpuid_tsx(td_inst, vm_ssh_key):
    """
    Get the TSX related info from EBX returned by cpuid
    More details of this can be found in the SDM (Software Developer's Manual)
    CPUID - CPU Identification, Volume 2. Instruction Set Reference.
      Initial EAX Value: 07H
      EBX Bit 04: HLE (Hardware Lock Elision, little edian, and #0 is the first bit)
      EBX Bit 11: RTM (Restricted Transactional Memory, little edian, and #0 is the first bit)
    """
    cpuid_7_ebx = get_cpuid_info(td_inst, vm_ssh_key, "7", "ebx")
    bit_hle = 1 & (cpuid_7_ebx >> 4)
    LOG.info("cpuid tsx bit 4 %d", bit_hle)
    bit_rtm = 1 & (cpuid_7_ebx >> 11)
    LOG.info("cpuid tsx bit 11 %d", bit_rtm)
    return bit_hle, bit_rtm


def get_msr_tsx(td_inst, vm_ssh_key):
    """
    Get the MSR value of TSX
    More details of this can be found in the SDM (Software Developer's Manual)
    Volume 4. Model Specific Registers.

      Register address: 10AH
      Architectural MSR Name: IA32_ARCH_CAPABILITIES
      MSR Description: Enumeration of Architectural Features
      BIT #7: TSX_CTRL. If 1, indicates presence of IA32_TSX_CTRL MSR.

      Register address: 122H
      Architectural MSR Name: IA32_TSX_CTRL
    """
    MSR_IA32_ARCH_CAPABILITIES = "0x10a"
    msr_info = get_msr_info(td_inst, vm_ssh_key, MSR_IA32_ARCH_CAPABILITIES)
    arch_cap = int(msr_info, 16)
    arch_cap_tsx = 1 & (arch_cap >> 7)

    MSR_IA32_TSX_CTRL = "0x122"
    msr_info = get_msr_info(td_inst, vm_ssh_key, MSR_IA32_TSX_CTRL)
    tsx_ctl = None
    if msr_info is not None:
        tsx_ctl = int(msr_info, 16)
    return arch_cap_tsx, tsx_ctl


def test_tsx_default(vm_factory, vm_ssh_key):
    """
    TSX is enabled by default.
    """
    td_inst = next(get_td_vm(vm_factory, vm_ssh_key, tsx_opt=None))

    bit_hle, bit_rtm = get_cpuid_tsx(td_inst, vm_ssh_key)
    assert (bit_hle & bit_rtm) == 1, "TSX is NOT enabled by default"

    msr_cap_tsx, msr_tsx_ctl = get_msr_tsx(td_inst, vm_ssh_key)
    assert (msr_cap_tsx == 1) and (msr_tsx_ctl is not None), "TSX is not available by default"

    LOG.info("TSX is enabled by default.")


def test_tsx_disabled(vm_factory, vm_ssh_key):
    """
    TSC deadline is disabled.
    """
    td_inst = next(get_td_vm(vm_factory, vm_ssh_key, tsx_opt=False))
    bit_hle, bit_rtm = get_cpuid_tsx(td_inst, vm_ssh_key)
    assert (bit_hle & bit_rtm) != 1, "TSX is NOT disabled"

    msr_cap_tsx, msr_tsx_ctl = get_msr_tsx(td_inst, vm_ssh_key)
    assert (msr_cap_tsx != 1) and (msr_tsx_ctl is None), "TSX is NOT disabled"

    LOG.info("TSX is disabled.")
