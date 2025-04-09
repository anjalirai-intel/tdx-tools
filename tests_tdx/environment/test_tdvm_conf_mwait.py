"""
TDX Guest check: MWAIT should be configurable
"""
import logging
import pytest
from environment.conf_utils import get_td_vm
from environment.conf_utils import get_cpuid_info


__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),    # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-image"),      # from artifacts.yaml
]


def get_cpuid_mwait(td_inst, vm_ssh_key):
    """
    Get the MONITOR/MWAIT bit from ECX returned by cpuid
    More details of this can be found in the SDM (Software Developer's Manual)
    CPUID - CPU Identification, Volume 2. Instruction Set Reference.
      Initial EAX Value: 01H
      ECX Bit #: 3 (the first bit is #0, little endian)
      Mnemonic: MONITOR
      Description: MONITOR/MWAIT. A value of 1 indicates the processor supports this feature.
    """
    cpuid_1_ecx = get_cpuid_info(td_inst, vm_ssh_key, "1", "ecx")
    mwait = 1 & (cpuid_1_ecx >> 3)
    LOG.info("cpuid mwait bit %d", mwait)
    return mwait


def test_mwait_default(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    MWAIT is disabled by default.
    """
    td_inst = next(get_td_vm(vm_factory, vm_ssh_key, vm_ssh_pubkey, mwait_opt=None))
    assert get_cpuid_mwait(td_inst, vm_ssh_key) == 0, "MWAIT should be disabled by default"
    LOG.info("MWAIT is disabled by default.")


def test_mwait_disabled(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    MWAIT is disabled.
    """
    td_inst = next(get_td_vm(vm_factory, vm_ssh_key, vm_ssh_pubkey, mwait_opt="off"))
    assert get_cpuid_mwait(td_inst, vm_ssh_key) == 0, "MWAIT is NOT disabled"
    LOG.info("MWAIT is disabled.")


def test_mwait_enabled(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    MWAIT is enabled.
    """
    td_inst = next(get_td_vm(vm_factory, vm_ssh_key, vm_ssh_pubkey, mwait_opt="on"))
    assert get_cpuid_mwait(td_inst, vm_ssh_key, vm_ssh_pubkey) == 1, "MWAIT is NOT enabled"
    LOG.info("MWAIT is enabled.")
