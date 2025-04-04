"""
This test module provides the basic selected ltp workload testing for TDVM
This benchmark test case is designed reference to :
         https://github.com/linux-test-project/ltp/
"""
import logging
import os
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_name("bat-ltp-td-centos8"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
    pytest.mark.vm_image("latest-guest-image"),
]


# pylint: disable=redefined-outer-name
@pytest.fixture(scope="module")
def td_instance_with_ssh(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    New mark for the vm factory to create different VM.
    """
    td_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=VMSpec.model_large())

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # Copy a "skiptest" file to guest image. This can be used to skip LTP test
    # Please see cmdline in syscalls as an example
    this_dir = os.path.dirname(os.path.realpath(__file__))
    skiptest = f"{this_dir}/skiptest"
    ltp_setup = f"{this_dir}/ltp_setup.sh"
    td_inst.image.copy_in(ltp_setup, "/root/")
    td_inst.image.copy_in(skiptest, "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    td_inst.wait_for_ssh_ready()

    command_list = [
        'cd /root/',
        'chmod +x ltp_setup.sh',
        './ltp_setup.sh',
        'cp -f /root/skiptest /opt/ltp/',
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"
    return td_inst


def common_ltp_test(td_inst, ssh_key, cmdline):
    """
    Common LTP test routine
    """
    LOG.info("Create TD guest to run ltp benchmark")

    runner = td_inst.ssh_run(cmdline.split(), ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"


@pytest.mark.bat
def test_tdvm_ltp_mm(td_instance_with_ssh, vm_ssh_key):
    """
    Run ltp memory test
    Ref: https://github.com/linux-test-project/ltp/tree/master/testcases/kernel/mem
    """
    common_ltp_test(td_instance_with_ssh, vm_ssh_key, "/opt/ltp/runltp -f mm")


@pytest.mark.regression
def test_tdvm_ltp_syscalls(td_instance_with_ssh, vm_ssh_key):
    """
    Run ltp syscalls test
    Ref: https://github.com/linux-test-project/ltp/tree/master/testcases/kernel/syscalls
    """
    LOG.info("Create TD guest to run ltp syscalls")
    # Test "ftruncate04" and "ftruncate04_64" will be skipped.
    # Reason: They rely on kernel config "CONFIG_MANDATORY_FILE_LOCKING=y"
    # but this config is supported in SPR BKC kernel anymore.
    # For ubuntu guest, please use /dev/vda1
    # For rhel guest, please use /dev/vda3
    common_ltp_test(td_instance_with_ssh, vm_ssh_key,
                    '''ln -s /dev/vda1 /dev/root && /opt/ltp/runltp -f syscalls
                    -S skiptest && unlink /dev/root''')


@pytest.mark.bat
def test_tdvm_ltp_smoketest(td_instance_with_ssh, vm_ssh_key):
    """
    Run ltp smoke test
    Ref: https://github.com/linux-test-project/ltp/blob/master/runtest/smoketest
    """
    LOG.info("Create TD guest to run ltp smoketest")
    common_ltp_test(td_instance_with_ssh, vm_ssh_key,
                    "/opt/ltp/runltp -f smoketest -S skiptest")


@pytest.mark.regression
def test_tdvm_ltp_numa(td_instance_with_ssh, vm_ssh_key):
    """
    Run ltp numa test
    Ref: https://github.com/linux-test-project/ltp/tree/master/testcases/kernel/numa
    """
    LOG.info("Create TD guest to run ltp numa")
    common_ltp_test(td_instance_with_ssh, vm_ssh_key,
                    "/opt/ltp/runltp -f numa")


@pytest.mark.regression
def test_tdvm_ltp_crypto(td_instance_with_ssh, vm_ssh_key):
    """
    Run ltp crypto test
    Ref: https://github.com/linux-test-project/ltp/tree/master/testcases/kernel/crypto
    """
    LOG.info("Create TD guest to run ltp crypto")
    common_ltp_test(td_instance_with_ssh, vm_ssh_key,
                    "/opt/ltp/runltp -f crypto -S skiptest")


@pytest.mark.regression
def test_tdvm_ltp_containers(td_instance_with_ssh, vm_ssh_key):
    """
    Run ltp container test
    Ref: https://github.com/linux-test-project/ltp/tree/master/testcases/kernel/containers
    """
    LOG.info("Create TD guest to run ltp container")
    common_ltp_test(td_instance_with_ssh, vm_ssh_key,
                    "/opt/ltp/runltp -f containers")


@pytest.mark.skip(reason="")
def test_tdvm_ltp_network(td_instance_with_ssh, vm_ssh_key):
    """
    Run ltp container test
    Ref: https://github.com/linux-test-project/ltp/tree/master/testcases/network/netstress
    """
    LOG.info("Create TD guest to run ltp netstress")
    common_ltp_test(td_instance_with_ssh, vm_ssh_key,
                    "/opt/ltp/runltp -f net.features -S skiptest")
