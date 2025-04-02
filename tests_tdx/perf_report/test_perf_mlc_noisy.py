"""
Perform Noisy neighbor analysis for MLC
"""

import os
import logging
import threading
import uuid
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI, KernelCmdline, VMSpec
from pycloudstack.vmm import VMMLibvirt
from pycloudstack.vmimg import VMImage
from pycloudstack.vmguest import VMGuest
from pycloudstack.msr import MSR
from pycloudstack.dut import DUT

__author__ = 'cpio'

MAX_VM_NUM = 2
_TD_MUTEX = threading.Lock()

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-pts-image"),    # from artifacts.yaml
]

MSR_DISABLE_HW_PREFETCH = 0x2F  # 0x2F is for Sapphire Rapid, 0xF for core
MSR_ENABLE_HW_PREFETCH = 0x20   # 0x20 is for Sapphire Rapid
MSR_MISC_FEATURE_CONTROL = 0x1a4


def change_hw_prefetcher(newval):
    """
    Change the MSR of HW prefetcher to new value.
    """
    oldval = MSR.readmsr(MSR_MISC_FEATURE_CONTROL)
    LOG.info(" >> HW Prefetcher old value: 0x%02x", oldval)
    if oldval == newval:
        LOG.info(" >> No changes for HW prefetcher.")
        return oldval
    LOG.info(" >> Change the MSR from 0x%02x to 0x%02x", oldval, newval)
    assert MSR.writemsr(MSR_MISC_FEATURE_CONTROL, newval)
    return oldval


@pytest.fixture(scope='function')
def hw_pref_disable():
    """
    Setup and teardown the HW prefetcher
    """
    LOG.info('--> Disable HW Prefetcher MSR <--')
    oldval = change_hw_prefetcher(MSR_DISABLE_HW_PREFETCH)
    yield MSR_DISABLE_HW_PREFETCH
    LOG.info('--> Restore HW Prefetcher MSR <--')
    change_hw_prefetcher(oldval)


@pytest.fixture(scope='function')
def hw_pref_enable():
    """
    Setup and teardown the HW prefetcher
    """
    LOG.info('--> Enable HW Prefetcher MSR <--')
    oldval = change_hw_prefetcher(MSR_ENABLE_HW_PREFETCH)
    yield MSR_ENABLE_HW_PREFETCH
    LOG.info('--> Restore HW Prefetcher MSR <--')
    change_hw_prefetcher(oldval)


def create_vm(vm_insts, vm_kernel, vm_image, vm_type, available_cpu_ids):
    """
    used to create two different kinds of VM, and support THP disbaled and 4k hugepage
    """
    vm_id = str(uuid.uuid4())
    vm_name = f"{vm_type}-{vm_id}"
    image = VMImage(vm_image).clone(vm_name + ".qcow2")
    with _TD_MUTEX:
        cpu_ids = available_cpu_ids.get()

        # config hugepage size
        cmdobj = KernelCmdline()
        cmdobj.add_field_from_string("transparent_hugepage=never")

        vm_inst = VMGuest(image, guest_distro=DUT.get_distro(), name=vm_name, vmid=vm_id,
                          vmtype=vm_type, vmspec=VMSpec.model_base(), kernel=vm_kernel,
                          cmdline=cmdobj, vmm_class=VMMLibvirt, cpu_ids=cpu_ids, mem_numa=True)

        # customize the VM image
        vm_inst.image.copy_in(
            os.path.join(CURR_DIR, "mlc-perf.sh"), "/root/")

        # create and start VM instance
        try:
            vm_inst.create()
            vm_inst.start()
            vm_insts.append(vm_inst)
        except SystemError:
            vm_inst.destroy()

    vm_inst.wait_for_ssh_ready()


def ssh_run(vm_inst, vm_ssh_key, mlc_command):
    """
    using ssh to run mlc command
    """
    command_list = ['/root/mlc-perf.sh ' + vm_inst.vmtype + mlc_command]

    for cmd in command_list:
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"


@pytest.mark.parametrize("td_num", [1])
def test_mlc_idle_latency(vm_ssh_key, vm_image, vm_kernel, td_num,
                          vm_ssh_pubkey, output, hw_pref_disable):
    """
    Measure idle latency for a TD guest

    Note: no much difference between single vcpu or multiple vcpu
    """
    LOG.info("Create TD guest to run MLC benchmark")

    available_cpu_ids = DUT.get_cpuids_group(MAX_VM_NUM, 4)
    # create two type vms
    vm_insts = []
    jobs = []
    for i in range(td_num):
        job = threading.Thread(target=create_vm, args=(vm_insts, vm_kernel, vm_image,
                                                       VM_TYPE_TD, available_cpu_ids))
        job.start()
        jobs.append(job)
    for i in range(MAX_VM_NUM - td_num):
        job = threading.Thread(target=create_vm, args=(vm_insts, vm_kernel, vm_image,
                                                       VM_TYPE_EFI, available_cpu_ids))
        job.start()
        jobs.append(job)

    for t in jobs:
        t.join()

    if len(vm_insts) != MAX_VM_NUM:
        LOG.warning("create vms failed!")
        assert False

    # execute mlc concurrently
    threads = []
    mlc_command = '-idle-latency --idle_latency -b2g -t60 -c0 -i0 -e -r -l128'
    for i in range(MAX_VM_NUM):
        tmp = threading.Thread(target=ssh_run, args=(vm_insts[i], vm_ssh_key, mlc_command))
        tmp.start()
        threads.append(tmp)

    # wait all VMs finish tasks
    for t in threads:
        t.join()

    # destroy all VMs
    for i in range(MAX_VM_NUM):
        vm_insts[i].scp_out("/root/mlc-report/", output, vm_ssh_key)
        vm_insts[i].destroy()
        vm_insts[i].image.destroy()


@pytest.mark.parametrize("td_num", [1])
def test_mlc_max_bandwidth(vm_ssh_key, vm_kernel, vm_image, td_num,
                           vm_ssh_pubkey, output, hw_pref_enable):
    """
    Measure max bandwidth for a TD guest

    Note: All experiments use AVX-512 instructions "-Z" and access the data at 64 B granularity
    """
    LOG.info("Create TD guest to run MLC benchmark")

    available_cpu_ids = DUT.get_cpuids_group(MAX_VM_NUM, 4)
    # create two type vms
    vm_insts = []
    jobs = []
    for i in range(td_num):
        job = threading.Thread(target=create_vm, args=(vm_insts, vm_kernel, vm_image,
                                                       VM_TYPE_TD, available_cpu_ids))
        job.start()
        jobs.append(job)
    for i in range(MAX_VM_NUM - td_num):
        job = threading.Thread(target=create_vm, args=(vm_insts, vm_kernel, vm_image,
                                                       VM_TYPE_EFI, available_cpu_ids))
        job.start()
        jobs.append(job)

    for t in jobs:
        t.join()

    if len(vm_insts) != MAX_VM_NUM:
        LOG.warning("create vms failed!")
        assert False

    # execute mlc concurrently
    threads = []
    mlc_command = '-max-bandwidth --max_bandwidth -b1g -Z -e -c0 -k1-3'
    for i in range(MAX_VM_NUM):
        tmp = threading.Thread(target=ssh_run, args=(vm_insts[i], vm_ssh_key, mlc_command))
        tmp.start()
        threads.append(tmp)

    # wait all VMs finish tasks
    for t in threads:
        t.join()

    # destroy all VMs
    for i in range(MAX_VM_NUM):
        vm_insts[i].scp_out("/root/mlc-report/", output, vm_ssh_key)
        vm_insts[i].destroy()
        vm_insts[i].image.destroy()
