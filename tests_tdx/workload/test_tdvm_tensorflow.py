"""
This test module provides the basic tensorflow workload testing for TDVM
This test case is designed reference to :
    https://software.intel.com/content/www/us/en/develop/articles/containers/mobilenetv1-fp32-inference-tensorflow-container.html
"""
import os
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_name("bat-tensorflow-td-centos8"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
    pytest.mark.vm_image("latest-guest-test-image"),
]


@pytest.mark.bat
def test_tdvm_tf(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Run a tensorflow sample application
    Ref: https://software.intel.com/content/www/us/en/develop/articles/containers/ \
        mobilenetv1-fp32-inference-tensorflow-container.html
    Use docker image:intel/image-recognition:tf-latest-mobilenet-v1-fp32-inference

    Test Steps:
    1. start VM
    2. Run remote command "systemctl status docker" to check the service's status
    3. Run remote command "systemctl start docker" to force start service docker
    4. Run remote command "docker ps" to ensure the docker service is ready
    5. Run remote command "docker run ... " to start tensorflow benchmark
    """
    LOG.info("Create TD guest to test tensorflow")
    td_inst = vm_factory.new_vm(VM_TYPE_TD)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    td_inst.wait_for_ssh_ready()

    command_list = [
        'systemctl start docker',
        'docker ps',
        '''
        docker run
        --env DATASET_DIR=/root/tf/data
        --env OUTPUT_DIR=/root/tf/log
        --env http_proxy=%s
        --env https_proxy=%s
        --volume /root/tf/data:/root/tf/data
        --volume /root/tf/log:/root/tf/log
        --privileged --init -t
        intel/image-recognition:tf-latest-mobilenet-v1-fp32-inference
        /bin/bash quickstart/fp32_batch_inference.sh
        ''' % (os.getenv('http_proxy'), os.getenv('https_proxy'))
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"


@pytest.mark.nontme
def test_legacy_tf(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Run a tensorflow sample application
    Ref: https://software.intel.com/content/www/us/en/develop/articles/containers/ \
        mobilenetv1-fp32-inference-tensorflow-container.html
    Use docker image:intel/image-recognition:tf-latest-mobilenet-v1-fp32-inference

    Test Steps:
    1. start VM
    2. Run remote command "systemctl status docker" to check the service's status
    3. Run remote command "systemctl start docker" to force start service docker
    4. Run remote command "docker ps" to ensure the docker service is ready
    5. Run remote command "docker run ... " to start tensorflow benchmark
    """
    LOG.info("Create TD guest to test tensorflow")
    td_inst = vm_factory.new_vm(VM_TYPE_LEGACY)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    td_inst.wait_for_ssh_ready()

    command_list = [
        'systemctl start docker',
        'docker ps',
        '''
        docker run
        --env DATASET_DIR=/root/tf/data
        --env OUTPUT_DIR=/root/tf/log
        --env http_proxy=%s
        --env https_proxy=%s
        --volume /root/tf/data:/root/tf/data
        --volume /root/tf/log:/root/tf/log
        --privileged --init -t
        intel/image-recognition:tf-latest-mobilenet-v1-fp32-inference
        /bin/bash quickstart/fp32_batch_inference.sh
        ''' % (os.getenv('http_proxy'), os.getenv('https_proxy'))
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"
