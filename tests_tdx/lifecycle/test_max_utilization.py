"""
This module provide the case to test boot with 80% utilization of host CPU and available memory

"""

import logging
import psutil
import pytest
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_STATE_RUNNING, VM_TYPE_EFI, VM_TYPE_TD, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


testdata = [
    (VM_TYPE_EFI),
    (VM_TYPE_LEGACY),
]


total_cores = psutil.cpu_count()
cores = int(total_cores * 0.4)
memsize = int(psutil.virtual_memory().available / 1000 * 0.8)
vmspec = VMSpec(sockets=2, cores=cores, memsize=memsize)


@pytest.mark.parametrize("vm_type", testdata)
def test_efi_legacy_max_utilization(vm_factory, vm_type):
    """
    Test boot and destroy EFI/Legacy guest with 80% host resource
    """

    inst = vm_factory.new_vm(vm_type, vmspec=vmspec, auto_start=True)

    assert inst.wait_for_state(VM_STATE_RUNNING), "Boot fail"
    assert inst.wait_for_ssh_ready(), "Boot timeout"

    inst.destroy()


@pytest.mark.repeat(50)
def test_tdvm_max_utilization(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Test boot and destroy TD guest with 80% host resource in cycling
    """

    inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vmspec)

    inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    inst.create()
    inst.start()

    assert inst.wait_for_state(VM_STATE_RUNNING), "Boot fail"
    assert inst.wait_for_ssh_ready(), "Boot timeout"

    cmd_list = [
        'systemctl start redis',
        'redis-benchmark -n 1000000 -t get,set > /dev/null',
        'systemctl stop redis'
        ]
    for cmd in cmd_list:
        runner = inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    inst.destroy()
