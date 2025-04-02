"""
This test module provides the phoronix testing for TD, non-TD VMs
"""
import os
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD_PERF, VM_TYPE_EFI_PERF, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name,redefined-outer-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifactory.ini
    pytest.mark.vm_image("latest-pts-image"),            # from artifactory.ini
]

pts_test_conf = [(VM_TYPE_EFI_PERF, VMSpec.model_large(), 'efi-large'),  # noqa: E241
                 (VM_TYPE_TD_PERF, VMSpec.model_large(), 'td-large')]          # noqa: E241


@pytest.fixture(scope="module", params=pts_test_conf)
def vm_instance_and_type(vm_factory, _vm_ssh_pubkey, request, output):
    """
    New mark for the vm factory to create different VM.
    """
    vm_type = request.param[0]
    vm_model = request.param[1]
    t_name = request.param[2]
    vm_inst = vm_factory.new_vm(vm_type, vmspec=vm_model)

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready()
    yield vm_inst, t_name
    vm_inst.destroy()
    out_file = f"/root/{t_name}.csv"
    vm_inst.image.copy_out(out_file, output)


def run_pts_test_case(vm_instance_and_type, vm_ssh_key, test_case):
    """
    Common phoronix test routine
    Run phoronix benchmark test
    Ref: https://www.phoronix-test-suite.com/
    Test Steps:
    1. start VM
    2. Run remote command "phoronix-test-suite install pts/TESTS"
    3. Run remote command "phoronix-test-suite batch-run pts/TESTS"
    4. Run remote command "phoronix-test-suite result-file-to-text cpio"

    Note:
    1. Must to set proxy due to phoronix will update tests when run any test case
    2. Must to set environment variable TEST_RESULTS_NAME which is used to save the results after
       the test is completed
    """
    vm_inst = vm_instance_and_type[0]
    t_name = vm_instance_and_type[1]
    pts_tests = test_case

    # Enable cpuidle-haltpoll driver for osbench and cassandra
    if "osbench" in pts_tests or "cassandra" in pts_tests:
        command = "modprobe cpuidle-haltpoll force=Y"
        runner = vm_inst.ssh_run(command.split(), vm_ssh_key)
        assert runner.retcode == 0, "Fail to enable cpuidle_haulpoll driver in guest VM."

    cmd = f'''
    http_proxy={os.getenv('http_proxy')} https_proxy={os.getenv('https_proxy')}
    phoronix-test-suite install pts/{pts_tests}  &&
    TEST_RESULTS_NAME=cpio phoronix-test-suite batch-run pts/{pts_tests}  &&
    phoronix-test-suite result-file-to-text cpio
    '''

    LOG.debug(cmd)
    runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"
    cmd = f'''
    phoronix-test-suite result-file-to-csv cpio  &&
    mv /root/cpio.csv /root/{t_name}.csv &&
    cat /root/{t_name}.csv &&
    sync &&
    sleep 2
    '''
    runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"


def test_pts_7zip(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case compress-7zip
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "compress-7zip-1.9.0")


def test_pts_mbw(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case mbw
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "mbw-1.0.0")


def test_pts_cachebench(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case cachebench
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "cachebench-1.1.2")


def test_pts_glibc_bench(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case glibc-bench
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "glibc-bench-1.7.2")


def test_pts_openssl(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case openssl
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "openssl-3.0.1")


def test_pts_osbench(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case osbench
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "osbench-1.0.2")


def test_pts_ctx(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case ctx-clock
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "ctx-clock-1.0.0")


def test_pts_apache(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case apache
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "apache-2.0.1")


def test_pts_nginx(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case nginx
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "nginx-2.0.1")


def test_pts_tf_lite(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case tensorflow-lite
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "tensorflow-lite-1.1.0")


def test_pts_numpy(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case numpy
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "numpy-1.2.1")


def test_pts_mariadb(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case mariadb
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "mysqlslap-1.3.0")


def test_pts_postgresql(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case postgresql
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "pgbench-1.11.0")


def test_pts_cassandra(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case cassandra
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "cassandra-1.1.1")


def test_pts_sysbench(vm_instance_and_type, vm_ssh_key):
    """
    Run sysbench
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "sysbench-1.1.0")


def test_pts_mlc(vm_instance_and_type, vm_ssh_key):
    """
    Run phoronix test case intel-mlc
    """
    run_pts_test_case(vm_instance_and_type, vm_ssh_key,
                      "intel-mlc-1.0.0")
