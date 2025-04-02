"""
MLC performance testing for TD and non-TD VM guest

Prerequistes
============
1. Bind the VM to CPU and memory, for example:

    <vcpu placement='static' cpuset='35-46'>1</vcpu>
    <cputune>
        <vcpupin vcpu='0' cpuset='39'/>
        <vcpupin vcpu='1' cpuset='40'/>
        <vcpupin vcpu='2' cpuset='41'/>
        <vcpupin vcpu='3' cpuset='42'/>
        <iothreadpin iothread='1' cpuset='38'/>
    </cputune>
    <numatune>
        <memory mode='strict' nodeset='0'/>
    </numatune>

2. Fix the CPU frequency
    sudo cpupower frequency-set --max 2500000 --min 2500000

3. Set CPU performance strategy
    sudo cpupower frequency-set -g performance

"""

import os
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI
from pycloudstack.msr import MSR

__author__ = 'cpio'

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-image"),    # from artifacts.yaml
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


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD, VM_TYPE_EFI])
def test_mlc_idle_latency(vm_factory, vm_ssh_key, vm_ssh_pubkey, vm_type, output, hw_pref_disable):
    """
    Measure idle latency for a TD guest

    Note: no much difference between single vcpu or multiple vcpu
    """
    LOG.info("Create TD guest to run MLC benchmark")
    vm_inst = vm_factory.new_vm(vm_type)

    # customize the VM image
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "mlc-perf.sh"), "/root/")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready()

    if vm_type is VM_TYPE_TD:
        case_name = "td"
    else:
        case_name = "legacy"

    command_list = ['/root/mlc-perf.sh ' +
                    case_name + '-idle-latency --idle_latency -b2g -t10 -c0 -i0 -e -r -l128']

    for cmd in command_list:
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.destroy()
    vm_inst.image.copy_out("/root/mlc-report/", output)


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD, VM_TYPE_EFI])
@pytest.mark.parametrize("rw_type", ['-R', '-W3', '-W2', '-W5', '-W7', '-W8', '-W6'])
def test_mlc_loaded_latency(vm_factory, vm_ssh_key, vm_ssh_pubkey, vm_type, rw_type, output,
                            hw_pref_enable):
    """
    Measure loaded latency for a TD guest
    """
    LOG.info("Create TD guest to run MLC benchmark")
    vm_inst = vm_factory.new_vm(vm_type)

    # customize the VM image
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "mlc-perf.sh"), "/root/")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready()

    if vm_type is VM_TYPE_TD:
        case_name = "td"
    else:
        case_name = "legacy"

    command_list = ['/root/mlc-perf.sh ' +
                    case_name + '-loaded-latency' + rw_type +
                    ' --loaded_latency -d0 -b1g -t30 -k1-3 -c0 -e -K1 -r ' + rw_type]

    for cmd in command_list:
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.destroy()
    vm_inst.image.copy_out("/root/mlc-report/", output)


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD, VM_TYPE_EFI])
def test_mlc_max_bandwidth(vm_factory, vm_ssh_key, vm_ssh_pubkey, vm_type, output, hw_pref_enable):
    """
    Measure max bandwidth for a TD guest

    Note: All experiments use AVX-512 instructions "-Z" and access the data at 64 B granularity
    """
    LOG.info("Create TD guest to run MLC benchmark")
    vm_inst = vm_factory.new_vm(vm_type)

    # customize the VM image
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "mlc-perf.sh"), "/root/")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready()

    if vm_type is VM_TYPE_TD:
        case_name = "td"
    else:
        case_name = "legacy"

    command_list = [
        '/root/mlc-perf.sh ' + case_name + '-max-bandwidth --max_bandwidth -Z -e -r'
    ]

    for cmd in command_list:
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.destroy()
    vm_inst.image.copy_out("/root/mlc-report/", output)


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD, VM_TYPE_EFI])
def test_tdvm_mlc_peak_injection_bandwidth(vm_factory, vm_ssh_key, vm_ssh_pubkey, vm_type, output,
                                           hw_pref_enable):
    """
    Measure peak injection bandwidth for a TD guest
    """
    LOG.info("Create TD guest to run MLC benchmark")
    vm_inst = vm_factory.new_vm(vm_type)

    # customize the VM image
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "mlc-perf.sh"), "/root/")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready()

    if vm_type is VM_TYPE_TD:
        case_name = "td"
    else:
        case_name = "legacy"

    command_list = ['/root/mlc-perf.sh ' +
                    case_name + '-peak-injection-bandwidth --peak_injection_bandwidth -K1 -e -r']

    for cmd in command_list:
        runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

    vm_inst.destroy()
    vm_inst.image.copy_out("/root/mlc-report/", output)
