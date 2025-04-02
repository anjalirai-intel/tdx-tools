"""
Test for debug registers simulated by KVM
"""

import os
from pycloudstack.cmdrunner import NativeCmdRunner

__author__ = 'cpio'


def test_tdvm_debug_inside():
    """
    Run debug on TD host.
    Ref: https://gitlab.com/kvm-unit-tests/kvm-unit-tests/-/blob/master/x86/debug.c
    """

    test_bin = os.path.join(os.path.dirname(__file__), "kvm_unit_prebuilts", "debug")

    runner = NativeCmdRunner([test_bin])
    runner.runwait()
    assert runner.retcode == 0, f"Failed to run {test_bin}"
