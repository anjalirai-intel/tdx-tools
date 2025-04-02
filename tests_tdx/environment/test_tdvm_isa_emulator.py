"""
Test for instruction set architecture (ISA) simulated by KVM
"""

import os
from pycloudstack.cmdrunner import NativeCmdRunner

__author__ = 'cpio'


def test_tdvm_isa_emulator():
    """
    Run emulator on TD host.
    Ref: https://gitlab.com/kvm-unit-tests/kvm-unit-tests/-/blob/master/x86/emulator.c
    """

    test_bin = os.path.join(os.path.dirname(__file__), "kvm_unit_prebuilts", "emulator")

    runner = NativeCmdRunner([test_bin])
    runner.runwait()
    assert runner.retcode == 0, f"Failed to run {test_bin}"
