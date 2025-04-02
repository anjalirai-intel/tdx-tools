"""
TDX Guest check: TSC deadline should be configurable
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


def get_cpuid_tsc_deadline(td_inst, vm_ssh_key):
    """
    Get the TSC deadline bit from ECX returned by cpuid
    More details of IA32_TSC_DEADLINE can be found in the SDM (Software Developer's Manual)
    Volume 2. Instruction Set Reference.
      Bit #: 24 (little edian, and #0 is the first bit)
      Mnemonic: TSC-Deadline
      Description: A value of 1 indicates that the processor’s local APIC timer supports one-shot
    operation using a TSC deadline value.
    """
    cpuid_1_ecx = get_cpuid_info(td_inst, vm_ssh_key, "1", "ecx")
    tsc_deadline = 1 & (cpuid_1_ecx >> 24)
    LOG.info("cpuid tsc_deadline bit %d", tsc_deadline)
    return tsc_deadline


def get_msr_tsc_deadline(td_inst, vm_ssh_key):
    """
    Get the MSR value of TSC deadline
    More details of IA32_TSC_DEADLINE can be found in the SDM (Software Developer's Manual)
    Volume 4. Model Specific Registers.
      Register address: 6E0H
      Architectural MSR Name: IA32_TSC_DEADLINE
      MSR Description: TSC Target of Local APIC’s TSC Deadline Mode (R/W) if "CPUID.01H:ECX.[24] = 1".
    """
    MSR_IA32_TSC_DEADLINE="0x6e0"
    return get_msr_info(td_inst, vm_ssh_key, MSR_IA32_TSC_DEADLINE)


def test_tsc_deadline_default(vm_factory, vm_ssh_key):
    """
    TSC deadline is enabled by default.
    """
    tsc_deadline_opt = None
    td_inst = next(get_td_vm(vm_factory, vm_ssh_key, tsc_deadline_opt))
    assert get_cpuid_tsc_deadline(td_inst, vm_ssh_key) == 1, "TSC deadline is NOT enabled by default"
    assert get_msr_tsc_deadline(td_inst, vm_ssh_key) is not None, "TSC deadline MSR is not available by default"
    LOG.info("TSC deadline is enabled by default.")


def test_tsc_deadline_disabled(vm_factory, vm_ssh_key):
    """
    TSC deadline is disabled.
    """
    tsc_deadline_opt = False
    td_inst = next(get_td_vm(vm_factory, vm_ssh_key, tsc_deadline_opt))
    assert get_cpuid_tsc_deadline(td_inst, vm_ssh_key) == 0, "TSC deadline is NOT disabled"
    assert get_msr_tsc_deadline(td_inst, vm_ssh_key) is None, "TSC deadline MSR is available when disabled"
    LOG.info("TSC deadline is disabled.")
