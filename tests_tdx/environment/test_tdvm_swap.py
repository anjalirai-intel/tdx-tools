"""
Test SWAP functionality within TD guest
Recommended System Swap Space from RedHat installation guide
|Amount of RAM in the system |Recommended swap space	         |Recommended swap space if
                                                                  allowing for hibernation
|less than 2 GB	             |2 times the amount of RAM	         |3 times the amount of RAM
|2 GB - 8 GB	             |Equal to the amount of RAM         |2 times the amount of RAM
|8 GB - 64 GB	             |4GB to 0.5 times the amount of RAM |1.5 times the amount of RAM
|more than 64 GB	         |workload dependent (at least 4GB)	 |hibernation not recommended
"""

import logging
import os
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

testdata = [
    (VM_TYPE_TD, 2 * 1024 * 1024, 2048),
    (VM_TYPE_TD, 3 * 1024 * 1024, 3072),
    (VM_TYPE_EFI, 1 * 1024 * 1024, 2048),
    (VM_TYPE_EFI, 2 * 1024 * 1024, 2048),
    (VM_TYPE_EFI, 3 * 1024 * 1024, 3072),
]


@pytest.mark.parametrize("vm_type, mem_size, swap_count", testdata)
def test_tdvm_swap(vm_factory, vm_ssh_pubkey, vm_ssh_key, vm_type, mem_size, swap_count):
    """
    Test SWAP functionality within TD guest.
    """

    LOG.info("Create TD guest")
    vmspec = VMSpec.model_base()
    vmspec.memsize = mem_size
    vm_inst = vm_factory.new_vm(vm_type, vmspec=vmspec)

    # customize the VM image
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"

    # Make swapfile in TD guest
    this_dir = os.path.dirname(os.path.realpath(__file__))
    script_file = f"{this_dir}/swap/make_swap.sh"
    runner = vm_inst.scp_in(script_file, "/opt/", vm_ssh_key)

    # Generate a swapfile with specific size
    cmd = f'/bin/bash /opt/make_swap.sh {swap_count}'
    runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to make swapfile"

    # Run LTP - mm - swapping test cases
    cmdline = "/opt/ltp/runltp -f mm -s swapping"
    runner = vm_inst.ssh_run(cmdline.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute LTP swapping testcase"


@pytest.mark.regression
def test_tdvm_swap_regression(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Test SWAP functionality within TD guest.
    Isolate this test for regression.
    """

    LOG.info("Create TD guest")
    vmspec = VMSpec.model_base()
    vmspec.memsize = 1 * 1024 * 1024
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vmspec)

    # customize the VM image
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"

    # Make swapfile in TD guest
    this_dir = os.path.dirname(os.path.realpath(__file__))
    script_file = f"{this_dir}/swap/make_swap.sh"
    runner = vm_inst.scp_in(script_file, "/opt/", vm_ssh_key)

    # Generate a swapfile with specific size
    cmd = f'/bin/bash /opt/make_swap.sh {2048}'
    runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to make swapfile"

    # Run LTP - mm - swapping test cases
    cmdline = "/opt/ltp/runltp -f mm -s swapping"
    runner = vm_inst.ssh_run(cmdline.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute LTP swapping testcase"
