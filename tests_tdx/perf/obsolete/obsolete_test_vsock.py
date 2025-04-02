"""
vsocket performance test for TD, non-TD guest.

This test depends on tool iperf-vsock:
  https://github.com/stefano-garzarella/iperf-vsock

This tool is not available from any repo, so it is provided as a pre-built binary file,
Located in directory iperf-vsock

"""
import os
import logging
import time
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY, VMSpec
from pycloudstack.cmdrunner import NativeCmdRunner

__author__ = 'cpio'

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-test-image"),    # from artifacts.yaml
]


def _create_vm_for_vsock_test(vm_factory, vm_type, vm_ssh_pubkey):
    '''
    Common vsocket test case routine
    1. Create vm guest
    2. Copy pre-built binanry (iperf-vsock, libiperf.so.0) to VM
    '''
    vm_inst = vm_factory.new_vm(vm_type, vmspec=VMSpec.model_large(), vsock=True)

    # customize the VM image
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "iperf-vsock", "iperf3"), "/root/")
    vm_inst.image.copy_in(
        os.path.join(CURR_DIR, "iperf-vsock", "libiperf.so.0"), "/root/")

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()

    return vm_inst


@pytest.mark.parametrize('vm_type', [VM_TYPE_TD, VM_TYPE_LEGACY])
def test_vsock_guest_as_server(vm_factory, vm_ssh_key, vm_ssh_pubkey,
                               vm_type):
    """
    Collect vsocket performance for TD, non-TD guest
    Test Steps:
    1. Start VM with vsock is enabled
    2. Copy pre-built binanry (iperf-vsock, libiperf.so.0) to VM
    3. Run remote command "iperf-vsock --vsock -s" to create server
    4. Run native command "iperf-vsock --vsock -c 3" to create a client
    5. Collect the result

    Note:
    The tool iperf-vsock depends on the library libiperf.so, which has the same name as the file
    provided by the package iperf3 in the centos repo. Therefore, the environment variable
    LD_LIBRARY_PATH needs to be set at runtime to specify the path where libiperf.so is located.
    """
    LOG.info("vsock performance test")
    vm_inst = _create_vm_for_vsock_test(vm_factory, vm_type, vm_ssh_pubkey)

    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"

    remote_command = 'LD_LIBRARY_PATH=/root ./iperf3 --vsock -s'

    server = vm_inst.ssh_run(remote_command.split(), vm_ssh_key, no_wait=True)
    time.sleep(5)

    native_tool_path = os.path.join(CURR_DIR, "iperf-vsock")
    native_cmd = f'{native_tool_path}/iperf3 --vsock -c 3'
    runtime_env = os.environ
    runtime_env["LD_LIBRARY_PATH"] = os.path.join(CURR_DIR, "iperf-vsock")
    client = NativeCmdRunner(native_cmd.split())
    client.env = runtime_env
    client.runwait()
    server.terminate()

    vm_inst.destroy()

    assert client.retcode == 0, "Client fail to run"


@pytest.mark.parametrize('vm_type', [VM_TYPE_TD, VM_TYPE_LEGACY])
def test_vsock_guest_as_client(vm_factory, vm_ssh_key, vm_ssh_pubkey,
                               vm_type):
    """
    Collect vsocket performance for TD, non-TD guest
    Test Steps:
    1. Start VM with vsock is enabled
    2. Copy pre-built binanry (iperf-vsock, libiperf.so.0) to VM
    3. Run native command "iperf-vsock --vsock -s" to create server
    4. Run remote command "iperf-vsock --vsock -c 2" to create a client
    5. Collect the result

    Note:
    The tool iperf-vsock depends on the library libiperf.so, which has the same name as the file
    provided by the package iperf3 in the centos repo. Therefore, the environment variable
    LD_LIBRARY_PATH needs to be set at runtime to specify the path where libiperf.so is located.
    """
    LOG.info("vsock performance test")
    vm_inst = _create_vm_for_vsock_test(vm_factory, vm_type, vm_ssh_pubkey)

    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"

    native_tool_path = os.path.join(CURR_DIR, "iperf-vsock")
    native_cmd = f'{native_tool_path}/iperf3 --vsock -s'
    runtime_env = os.environ
    runtime_env["LD_LIBRARY_PATH"] = os.path.join(CURR_DIR, "iperf-vsock")
    server = NativeCmdRunner(native_cmd.split())
    server.env = runtime_env
    server.runnowait()

    remote_command = 'LD_LIBRARY_PATH=/root ./iperf3 --vsock -c 2'

    client = vm_inst.ssh_run(remote_command.split(), vm_ssh_key, no_wait=False)
    time.sleep(5)

    server.terminate()

    vm_inst.destroy()

    assert client.retcode == 0, "Client fail to run"
