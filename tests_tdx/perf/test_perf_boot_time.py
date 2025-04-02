"""
Measure the boot time for non-TD OVMF guest and TD guest.

It should be a simplified version of the image that is used for boot time test.
Specified with "latest-pts-boot-image" in artifacts.yaml.

The sample rate can be specified using check_interval. To get a precision of 0.5s,
we set the check_interval as 0.2s (more than twice of the measured frequency).

"""
import logging
import time
import os
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI, BOOT_TYPE_GRUB, VMSpec
from pycloudstack.cmdrunner import NativeCmdRunner

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-pts-boot-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

HUGEPAGE_PATH = "/tmp/hugetlbtest"

# bind cpu/iothread
vm_cpus = {
    1:    list(range(0, 2)),
    2:    list(range(0, 3)),
    4:    list(range(0, 5)),
    8:    list(range(0, 9)),
    16:   list(range(0, 17)),
    32:   [33]+list(range(0, 32)),
    64:   [33]+list(range(0, 32))+list(range(48, 80)),
    128:  [33]+list(range(0, 32))+list(range(48, 80))+list(range(112, 144))+list(range(160, 192))
}

# create scaling up VMSpec based on core numbers
vm_spec_list = [VMSpec(cores=k) for k in vm_cpus]
vm_spec_list.append(VMSpec(cores = 128, memsize=864*1024*1024))


def set_hugepage(hugepage_path, hugepage_count):
    """
    Set hugepage_count in hugepage_path
    """
    if os.path.isfile(hugepage_path):
        with open(hugepage_path, 'w', encoding="utf8") as f:
            f.write(str(hugepage_count))
    else:
        LOG.error("Hugepage path does not exist.")
        pytest.fail()

    with open(hugepage_path, 'r', encoding="utf8") as f:
        host_hugepages = int(f.read())
    assert host_hugepages == hugepage_count, "Cannot allocate enough hugepages"

def prep_hugepage_path(memsize):
    """
    memsize is the memory size required by VM
    For memsize < 512G, use single node allocating hugepage
    For memsize > 512G, use 2 nodes allocating hugepage
    """
    memsize = int(memsize/1024)
    if memsize < 524288:
        # single node hugepage
        hugepage = int(memsize/2)
        path = '/sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages'
        set_hugepage(path, hugepage)
    else:
        # cross nodes hugepage
        hugepage = int(memsize/4)
        nodes = ['node0', 'node1']
        for node in nodes:
            path = f'/sys/devices/system/node/{node}/hugepages/hugepages-2048kB/nr_hugepages'
            set_hugepage(path, hugepage)

    #check if the HUGEPAGE_PATH exists
    if not os.path.exists(HUGEPAGE_PATH):
        os.makedirs(HUGEPAGE_PATH)

    # umount hugepage_path for TD
    cmd = f'findmnt --mountpoint {HUGEPAGE_PATH}'
    runner = NativeCmdRunner(cmd.split())
    runner.runwait()

    for i in range(len(runner.stdout) - 1):
        cmd = f'umount {HUGEPAGE_PATH}'
        runner = NativeCmdRunner(cmd.split())
        assert runner.runwait() == 0, "Fail to umount hugepage_path"
        i += 1

    # mount hugepage_path for TD
    cmd = f'mount -t tmpfs -o huge=always,size={memsize}M tmpfs {HUGEPAGE_PATH}'
    runner = NativeCmdRunner(cmd.split())
    assert runner.runwait() == 0, "Fail to mount hugepage_path"


@pytest.mark.repeat(5)
@pytest.mark.parametrize("vm_spec", vm_spec_list)
def test_td_vm(vm_factory, vm_spec):
    """
    Run benchmark on TD VM one by one but not concurrent.
    """

    # Prepare hugepage for test
    prep_hugepage_path(vm_spec.memsize)

    td_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vm_spec, boot=BOOT_TYPE_GRUB, cpu_ids=vm_cpus[vm_spec.cores],
    hugepages=True, hugepage_size="2M", hugepage_path=HUGEPAGE_PATH)

    start = time.time()
    td_inst.create()
    td_inst.start()

    assert td_inst.wait_for_ssh_ready(check_interval=0.2)
    boot_time = time.time() - start
    boot_time_log_str = f'boot time {boot_time}'
    LOG.info('---------------------------------------------------')
    LOG.info(boot_time_log_str)
    LOG.info('---------------------------------------------------')
    vm_factory.remove(td_inst)


@pytest.mark.repeat(5)
@pytest.mark.parametrize("vm_spec", vm_spec_list)
def test_ovmf_vm(vm_factory, vm_spec):
    """
    Run benchmark on OVMF VM one by one but not concurrent.
    """

    # Prepare hugepage for test
    prep_hugepage_path(vm_spec.memsize)

    ovmf_inst = vm_factory.new_vm(VM_TYPE_EFI, vmspec=vm_spec,boot=BOOT_TYPE_GRUB, cpu_ids=vm_cpus[vm_spec.cores],
    hugepages=True,hugepage_size="2M")

    start = time.time()
    ovmf_inst.create()
    ovmf_inst.start()

    assert ovmf_inst.wait_for_ssh_ready(check_interval=0.2)
    boot_time = time.time() - start
    boot_time_log_str = f'boot time {boot_time}'
    LOG.info('---------------------------------------------------')
    LOG.info(boot_time_log_str)
    LOG.info('---------------------------------------------------')
    vm_factory.remove(ovmf_inst)
