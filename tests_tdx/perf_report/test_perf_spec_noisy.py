"""
Perform Noisy neighbor analysis for SPECCPU and SPECJBB
Prerequistes
============
Need to use target image
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
from pycloudstack.dut import DUT

__author__ = 'cpio'

MAX_VM_NUM = 2
_TD_MUTEX = threading.Lock()

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-image"),    # from artifacts.yaml
]


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

        # create and start VM instance
        try:
            vm_inst.create()
            vm_inst.start()
            vm_insts.append(vm_inst)
        except SystemError:
            vm_inst.destroy()

    vm_inst.wait_for_ssh_ready()


def ssh_run(vm_inst, vm_ssh_key, cmd):
    """
    using ssh to connect vm and run commands
    """
    runner = vm_inst.ssh_run(cmd, vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"


@pytest.mark.parametrize("td_num", [1])
def test_specjbb(vm_ssh_key, vm_image, vm_kernel, td_num,
                 vm_ssh_pubkey, output):
    """
    Measure SPECJBB
    """
    LOG.info("Create guests to run SPECJBB")

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
    cmd = 'bash specjbb-jdk13.sh'
    for i in range(MAX_VM_NUM):
        tmp = threading.Thread(target=ssh_run, args=(vm_insts[i], vm_ssh_key, cmd))
        tmp.start()
        threads.append(tmp)

    # wait all VMs finish tasks
    for t in threads:
        t.join()

    # destroy all VMs
    for i in range(MAX_VM_NUM):
        vm_insts[i].scp_out("/opt/pkb/SPECjbb2015/jbb103/result", output, vm_ssh_key)
        vm_insts[i].destroy()
        vm_insts[i].image.destroy()


@pytest.mark.parametrize("td_num", [1])
def test_speccpu(vm_ssh_key, vm_kernel, vm_image, td_num,
                 vm_ssh_pubkey, output):
    """
    Measure SPECCPU
    """
    LOG.info("Create guests to run SPECCPU")

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
    cmd = 'bash speccpu.sh'
    for i in range(MAX_VM_NUM):
        tmp = threading.Thread(target=ssh_run, args=(vm_insts[i], vm_ssh_key, cmd))
        tmp.start()
        threads.append(tmp)

    # wait all VMs finish tasks
    for t in threads:
        t.join()

    # destroy all VMs
    for i in range(MAX_VM_NUM):
        vm_insts[i].scp_out("/root/specCPU17/result", output, vm_ssh_key)
        vm_insts[i].destroy()
        vm_insts[i].image.destroy()
