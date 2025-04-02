"""
Stability testings for single TDVM cycling with tensorflow workload includes:

- virsh suspend/resume
"""
import os
import time
import logging
import pytest

from pycloudstack.vmparam import VM_TYPE_TD, VM_STATE_RUNNING, VM_STATE_PAUSE, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_name("stability-single-td-centos8"),
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


@pytest.fixture(scope="module")
def tdvm_instance(vm_factory, vm_ssh_pubkey):
    """
    TDVM instance fixture
    """
    LOG.info("Create TD guest")
    vm_inst = vm_factory.new_vm(VM_TYPE_TD, VMSpec.model_large())
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    vm_inst.create()
    vm_inst.start()
    vm_inst.wait_for_ssh_ready()

    return vm_inst


# pylint: disable=redefined-outer-name
@pytest.mark.repeat(500)
def test_single_tdvm_suspend_resume_cycle(tdvm_instance, vm_ssh_key):
    """
    Test the basic lifecycle: virsh suspend/resume with workload
    Ref: https://software.intel.com/content/www/us/en/develop/articles/containers/ \
        mobilenetv1-fp32-inference-tensorflow-container.html

    Step 1: Create TD guest
    Step 2: suspend TD guest for 5 seconds
    Step 3: resume TD guest
    Step 4: run workload tensorflow
    Step 5: repeat step 2 ~ step 4 for cycling
    DPMO <= 2000
       1 defects / ( 1 TD guest * 500 cycles ) * 1000000 = 2000 DPMO

    NOTE: vm_factory will cleanup all created VM instance in its __del__ later,
          so do not clean them explicitly.
    """

    LOG.info("Suspend TD guest")
    tdvm_instance.suspend()
    ret = tdvm_instance.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    time.sleep(5)

    LOG.info("Resume TD guest")
    tdvm_instance.resume()
    ret = tdvm_instance.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"

    command_list = [
        'systemctl start docker',
        '''
        docker run
        --env DATASET_DIR=/root/tf/data
        --env OUTPUT_DIR=/root/tf/log
        --env http_proxy=%s
        --env https_proxy=%s
        --volume /root/tf/data:/root/tf/data
        --volume /root/tf/log:/root/tf/log
        --privileged --init -t
        intel/image-recognition:tf-2.4.0-mobilenet-v1-fp32-inference
        /bin/bash quickstart/fp32_batch_inference.sh
        ''' % (os.getenv('http_proxy'), os.getenv('https_proxy'))
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        runner = tdvm_instance.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"
