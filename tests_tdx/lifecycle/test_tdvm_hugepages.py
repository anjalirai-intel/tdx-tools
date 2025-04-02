"""
This test module provides a basic test for TDVM + hugepages.
"""

import logging
import os
import pytest

from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import VM_TYPE_TD, VMSpec

LOG = logging.getLogger(__name__)

HUGEPAGE_PATH_2M = "/dev/hugepages"
HUGEPAGE_PATH_1G = "/dev/hugepages1G"

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def _set_host_hugepages(hugepage_size, hugepage_count, verify=True):
    """
    1. Check whether we are dealing with 2M or 1G hugepages
    2. Allocate number of hugepages of appropriate size via sysfs
    3. Verify they were able to be allocated (optional)
    """
    if hugepage_size == "2M":
        hugepage_dir = "hugepages-2048kB"
    elif hugepage_size == "1G":
        hugepage_dir = "hugepages-1048576kB"
    else:
        LOG.error("Invalid hugepage size %d", hugepage_size)
        pytest.fail()

    hugepage_path = f"/sys/devices/system/node/node0/hugepages/{hugepage_dir}/nr_hugepages"

    if os.path.isfile(hugepage_path):
        with open(hugepage_path, 'w', encoding="utf8") as f:
            f.write(str(hugepage_count))
    else:
        LOG.error("Hugepage path does not exist.")
        pytest.fail()

    if verify:
        with open(hugepage_path, 'r', encoding="utf8") as f:
            host_hugepages = int(f.read())
        if host_hugepages != hugepage_count:
            LOG.warning("Expected %d; found only %d", hugepage_count, host_hugepages)
            LOG.warning("Memory may be too fragmented to create %d hugepages",
                        hugepage_count)
            LOG.warning("Try running this test after rebooting.")
            pytest.skip("Cannot allocate enough hugepages.")


def _enable_qemu_hugepage():
    """
    Restart libvirtd after /dev/hugepages* created
    or qemu will fail to create the TD
    """
    LOG.info("hugepage configured. Restart libvirtd.service")
    runner = NativeCmdRunner(["systemctl", "restart", "libvirtd.service"])
    assert runner.runwait() == 0


def _mount_host_hugepages(hugepage_size):
    """
    1. Check whether we are dealing with 2M or 1G hugepages
    2. Create and mount the appropriate directory if it doesn't already exist
    3. Restart libvirtd to avoid qemu failure
    """
    if hugepage_size == "2M":
        hugepage_dir = HUGEPAGE_PATH_2M
    elif hugepage_size == "1G":
        hugepage_dir = HUGEPAGE_PATH_1G
    else:
        LOG.error("Invalid hugepage size %s", hugepage_size)
        pytest.fail()
    # For now assume if it exists, it is also mounted
    if not os.path.isdir(hugepage_dir):
        os.mkdir(hugepage_dir)
        mount_cmd = f"mount -t hugetlbfs -o pagesize={hugepage_size} none {hugepage_dir}"
        runner = NativeCmdRunner(mount_cmd.split())
        runner.runwait()

    _enable_qemu_hugepage()


def get_free_hugepages_count(hugepage_size):
    """
    Get the count of free huge pages.
    """
    if hugepage_size == "2M":
        hugepage_dir = "hugepages-2048kB"
    elif hugepage_size == "1G":
        hugepage_dir = "hugepages-1048576kB"
    else:
        LOG.error("Invalid hugepage size %d", hugepage_size)
        pytest.fail()
    hugepage_path = f"/sys/devices/system/node/node0/hugepages/{hugepage_dir}/free_hugepages"
    cmd = f"cat {hugepage_path}"
    runner = NativeCmdRunner(cmd.split())
    runner.runwait()
    count = int(runner.stdout[0])
    return count

def test_tdvm_hugepages_2M(vm_factory):
    """
    1. Allocate 2M hugepages on host
    2. Create TD guest with 2M hugepages memory backing
    3. Ensure TD guest is reachable
    4. Deallocate hugepages on host
    """
    LOG.info("Allocate host 2M hugepages")
    _set_host_hugepages("2M", 512)
    _mount_host_hugepages("2M")
    free_count = get_free_hugepages_count("2M")
    assert free_count == 512
    LOG.info("Create TD guest with 2M hugepages")
    vmspec = VMSpec.model_base()
    vmspec.memsize = 1 * 1024 * 1024
    inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vmspec, auto_start=True,
                             hugepages=True, hugepage_size="2M", hugepage_path=HUGEPAGE_PATH_2M)
    assert inst.wait_for_ssh_ready(), "Could not reach TD"

    # Make sure hugepages are used by this VM's qemu process on host
    cmd = "ps -ef"
    runner = NativeCmdRunner(cmd.split())
    runner.runwait()
    results = runner.stdout
    for result in results:
        if inst.name in result:
            assert "/dev/hugepages" in result

    # Make sure persistent hugepages are in use from /proc/meminfo
    # There should be 512 huge pages in total. And the free huge page count should < 512.
    cmd = "cat /proc/meminfo"
    runner = NativeCmdRunner(cmd.split())
    runner.runwait()
    results = runner.stdout
    for result in results:
        if "HugePages_Total" in result:
            assert "512" in result
    free_count = get_free_hugepages_count("2M")
    assert free_count < 512
    assert free_count >= 0

    _set_host_hugepages("2M", 0, False)


@pytest.mark.skip(reason="1GB hugepage is not supported yet")
def test_tdvm_hugepages_1G(vm_factory):
    """
    1. Allocate 1G hugepages on host
    2. Create TD guest with 1G hugepages memory backing
    2. Ensure TD guest is reachable
    4. Deallocate hugepages on host
    """

    LOG.info("Allocate host 1G hugepages")
    _set_host_hugepages("1G", 2)
    _mount_host_hugepages("1G")
    LOG.info("Create TD guest with 1G hugepages")
    vmspec = VMSpec.model_base()
    vmspec.memsize = 2 * 1024 * 1024
    inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vmspec, auto_start=True,
                             hugepages=True, hugepage_size="1G", hugepage_path=HUGEPAGE_PATH_1G)
    assert inst.wait_for_ssh_ready(), "Could not reach TD"
    _set_host_hugepages("1G", 0, False)
