"""
Test the virio based bridge network throughput via perf3.

Pre-requisite:

1. iperf3 tool should be installed in VM image and host
2. firewalld within guest VM should be disabled or configured for iperf
3. Bridge network virbr0 was created by "virsh net-start default"

"""
import logging
import time
import datetime
import pytest

from pycloudstack.vmparam import VM_TYPE_TD_PERF, VM_TYPE_EFI_PERF, VMSpec
from pycloudstack.cmdrunner import NativeCmdRunner

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),
    pytest.mark.vm_image("latest-pts-image"),
]


def base_vm_instance(vm_factory, vm_type):
    """
    helper function to create an VM instance according to given type
    """
    vm_inst = vm_factory.new_vm(vm_type, vmspec=VMSpec.model_large(), driver="qemu")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    assert vm_inst.wait_for_ssh_ready()
    return vm_inst


def test_iperf_tcp_basic_host_to_td(vm_factory, vm_ssh_key, output):
    """
    TCP basic: Host (iperf client) ===> TD Guest (iperf server)
    """
    base_td = base_vm_instance(vm_factory, VM_TYPE_TD_PERF)

    base_td.ssh_run(['systemctl', 'stop', 'firewalld'], vm_ssh_key)

    server = base_td.ssh_run(
        ['iperf3', "-s", "--logfile",
         f"/tmp/iperf_tcp_basic_host_to_td_{DATE_SUFFIX}.log"],
        vm_ssh_key, no_wait=True)

    time.sleep(5)

    client = NativeCmdRunner(
        ['iperf3', '-c', base_td.get_ip(), "-f", "M", "-t", "60"])
    client.runwait()
    if client.retcode != 0:
        LOG.warning("Fail to execute iperf client")

    server.terminate()

    runner = base_td.scp_out(
        f"/tmp/iperf_tcp_basic_host_to_td_{DATE_SUFFIX}.log", output, vm_ssh_key)
    assert runner.retcode == 0

    vm_factory.remove(base_td)


def test_iperf_tcp_basic_host_to_efi(vm_factory, vm_ssh_key, output):
    """
    TCP basic: Host (iperf client) ===> EFI Guest (iperf server)
    """
    base_efi = base_vm_instance(vm_factory, VM_TYPE_EFI_PERF)

    base_efi.ssh_run(['systemctl', 'stop', 'firewalld'], vm_ssh_key)

    server = base_efi.ssh_run(
        ['iperf3', "-s", "--logfile",
         f"/tmp/iperf_tcp_basic_host_to_efi_{DATE_SUFFIX}.log"],
        vm_ssh_key, no_wait=True)

    time.sleep(5)

    client = NativeCmdRunner(
        ['iperf3', '-c', base_efi.get_ip(), "-f", "M", "-t", "60"])
    client.runwait()
    if client.retcode != 0:
        LOG.warning("Fail to execute iperf client")

    server.terminate()

    runner = base_efi.scp_out(
        f"/tmp/iperf_tcp_basic_host_to_efi_{DATE_SUFFIX}.log", output, vm_ssh_key)
    assert runner.retcode == 0

    vm_factory.remove(base_efi)


def test_iperf_udp_basic_host_to_td(vm_factory, vm_ssh_key, output):
    """
    UDP basic: Host (iperf client) ===> TD Guest (iperf server)
    """
    base_td = base_vm_instance(vm_factory, VM_TYPE_TD_PERF)

    base_td.ssh_run(['systemctl', 'stop', 'firewalld'], vm_ssh_key)

    server = base_td.ssh_run(
        ['iperf3', "-s", "--logfile",
         f"/tmp/iperf_udp_basic_host_to_td_{DATE_SUFFIX}.log"],
        vm_ssh_key, no_wait=True)

    time.sleep(5)

    client = NativeCmdRunner(
        ['iperf3', '-c', base_td.get_ip(), "-f", "M", "-u", "-t", "60"])
    client.runwait()
    if client.retcode != 0:
        LOG.warning("Fail to execute iperf client")

    server.terminate()

    runner = base_td.scp_out(
        f"/tmp/iperf_udp_basic_host_to_td_{DATE_SUFFIX}.log", output, vm_ssh_key)
    assert runner.retcode == 0

    vm_factory.remove(base_td)


def test_iperf_udp_basic_host_to_efi(vm_factory, vm_ssh_key, output):
    """
    UDP basic: Host (iperf client) ===> EFI Guest (iperf server)
    """
    base_efi = base_vm_instance(vm_factory, VM_TYPE_EFI_PERF)

    base_efi.ssh_run(['systemctl', 'stop', 'firewalld'], vm_ssh_key)

    server = base_efi.ssh_run(
        ['iperf3', "-s", "--logfile",
         f"/tmp/iperf_udp_basic_host_to_efi_{DATE_SUFFIX}.log"],
        vm_ssh_key, no_wait=True)

    time.sleep(5)

    client = NativeCmdRunner(
        ['iperf3', '-c', base_efi.get_ip(), "-f", "M", "-u", "-t", "60"])
    client.runwait()
    if client.retcode != 0:
        LOG.warning("Fail to execute iperf client")

    server.terminate()

    runner = base_efi.scp_out(
        f"/tmp/iperf_udp_basic_host_to_efi_{DATE_SUFFIX}.log", output, vm_ssh_key)
    assert runner.retcode == 0

    vm_factory.remove(base_efi)


def test_iperf_tcp_basic_td_to_td(vm_factory, vm_ssh_key, output):
    """
    TCP basic: TD Guest (iperf client) ===> TD Guest (iperf server)
    """
    base_td = base_vm_instance(vm_factory, VM_TYPE_TD_PERF)
    base_td2 = base_vm_instance(vm_factory, VM_TYPE_TD_PERF)

    LOG.debug("Wait for IP up for first TD VM: %s", base_td.get_ip())
    LOG.debug("Wait for IP up for second TD VM: %s", base_td2.get_ip())

    base_td.ssh_run(['systemctl', 'stop', 'firewalld'], vm_ssh_key)
    base_td2.ssh_run(['systemctl', 'stop', 'firewalld'], vm_ssh_key)

    server = base_td.ssh_run(
        ['iperf3', "-s", "--logfile",
         f"/tmp/iperf_tcp_basic_td_to_td_{DATE_SUFFIX}.log"],
        vm_ssh_key, no_wait=True)

    time.sleep(5)

    client = base_td2.ssh_run(
        ['iperf3', '-c', base_td.get_ip(), "-f", "M", "-t", "60"],
        vm_ssh_key)
    if client.retcode != 0:
        LOG.warning("Fail to execute iperf client")

    server.terminate()

    runner = base_td.scp_out(
        f"/tmp/iperf_tcp_basic_td_to_td_{DATE_SUFFIX}.log", output, vm_ssh_key)
    assert runner.retcode == 0

    vm_factory.remove(base_td)
    vm_factory.remove(base_td2)


def test_iperf_tcp_basic_efi_to_efi(vm_factory, vm_ssh_key, output):
    """
    TCP basic: EFI Guest (iperf client) ===> EFI Guest (iperf server)
    """
    base_efi = base_vm_instance(vm_factory, VM_TYPE_EFI_PERF)
    base_efi2 = base_vm_instance(vm_factory, VM_TYPE_EFI_PERF)

    LOG.debug("Wait for IP up for first EFI VM: %s", base_efi.get_ip())
    LOG.debug("Wait for IP up for second EFI VM: %s", base_efi2.get_ip())

    base_efi.ssh_run(['systemctl', 'stop', 'firewalld'], vm_ssh_key)
    base_efi2.ssh_run(['systemctl', 'stop', 'firewalld'], vm_ssh_key)

    server = base_efi.ssh_run(
        ['iperf3', "-s", "--logfile",
         f"/tmp/iperf_tcp_basic_efi_to_efi_{DATE_SUFFIX}.log"],
        vm_ssh_key, no_wait=True)

    time.sleep(5)

    client = base_efi2.ssh_run(
        ['iperf3', '-c', base_efi.get_ip(), "-f", "M", "-t", "60"],
        vm_ssh_key)
    if client.retcode != 0:
        LOG.warning("Fail to execute iperf client")

    server.terminate()

    runner = base_efi.scp_out(
        f"/tmp/iperf_tcp_basic_efi_to_efi_{DATE_SUFFIX}.log", output, vm_ssh_key)
    assert runner.retcode == 0

    vm_factory.remove(base_efi)
    vm_factory.remove(base_efi2)
