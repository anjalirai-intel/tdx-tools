"""
Stability testings for multiple TDVM cycling with tensorflow workload includes:

- virsh suspend/resume
"""
import os
import time
import threading
import logging
import pytest

from pycloudstack.vmparam import VM_TYPE_TD, VM_STATE_RUNNING, VM_STATE_PAUSE, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

_MAX_TD_GUEST = 25

_WORKLOAD_NGINX = [
    'sysctl -w net.ipv6.conf.all.disable_ipv6=1',
    'systemctl start nginx',
    'siege -q -r 30000 -b localhost',
    'systemctl stop nginx',
    'sysctl -w net.ipv6.conf.all.disable_ipv6=0',
]

_WORKLOAD_REDIS = [
    'systemctl start redis',
    'redis-benchmark -n 15000000 -t get,set > /dev/null',
    'systemctl stop redis',
]

_WORKLOAD_TF = [
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
    ''' % (os.getenv('http_proxy'), os.getenv('https_proxy')),
    'systemctl stop docker',
]

# Run y-cruncher twice, as the workload has to be smaller for this memsize
_WORKLOAD_YCRUNCHER = [
    '/root/y-cruncher/y-cruncher skip-warnings bench 250m',
    '/root/y-cruncher/y-cruncher skip-warnings bench 250m'
]

_WORKLOADS = [
    _WORKLOAD_NGINX,
    _WORKLOAD_REDIS,
    _WORKLOAD_TF,
    _WORKLOAD_YCRUNCHER,
]

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

vmspec = VMSpec.model_base()
vmspec.cores = 1
vmspec.memsize = 4 * 1024 * 1024


@pytest.fixture(scope="module")
def multi_vm_instances(vm_factory, vm_ssh_pubkey):
    """
    TD guest instance fixture
    """
    started_instances = []
    for index in range(_MAX_TD_GUEST):
        LOG.info("Creating %d TD", index)
        vm_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vmspec)
        vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
        vm_inst.create()
        vm_inst.start()
        started_instances.append(vm_inst)

    for item in vm_factory.vms.values():
        item.wait_for_ssh_ready()

    return started_instances


def worker(instance, vm_ssh_key, index, results):
    """
    The worker to launch workload for each TD guest in parallel:

    1. suspended for 5 seconds
    2. resumed
    3. run workload tensorflow

    """

    LOG.info("Suspend TD guest")
    instance.suspend()
    ret = instance.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    time.sleep(5)

    LOG.info("Resume TD guest")
    instance.resume()
    ret = instance.wait_for_state(VM_STATE_RUNNING)
    assert ret, "Resume timeout"

    command_list = _WORKLOADS[index % len(_WORKLOADS)]

    for cmd in command_list:
        retry = 3
        while retry > 0:
            runner = instance.ssh_run(cmd.split(), vm_ssh_key)
            results[index] = runner.retcode
            if results[index] == 0:
                break
            retry -= 1
            time.sleep(1)

        if results[index] != 0:
            break


# pylint: disable=W0621
@pytest.mark.repeat(1000)
def test_multi_tdvm_suspend_resume(multi_vm_instances, vm_ssh_key):
    """
    Test the basic lifecycle of multiple TD guests: virsh suspend/resume with workload
    Ref: https://software.intel.com/content/www/us/en/develop/articles/containers/ \
        mobilenetv1-fp32-inference-tensorflow-container.html

    Step 1: Create multiple TD guests
    Step 2: suspend TD guests for 5 seconds
    Step 3: resume TD guests
    Step 4: run workload tensorflow
    Step 5: repeat step 2 ~ step 4 for cycling
    DPMO <= 2000
       1 defects / ( 10 TD guest * 50 cycles ) * 1000000 = 2000 DPMO

    NOTE: vm_factory will cleanup all created VM instance in its __del__ later,
          so do not clean them explicitly.
    """

    jobs = []
    results = [-1] * _MAX_TD_GUEST
    for index in range(_MAX_TD_GUEST):
        td_job = threading.Thread(target=worker, args=(multi_vm_instances[index], vm_ssh_key, index, results))
        jobs.append(td_job)
        td_job.start()

    for job in jobs:
        job.join()

    for result in results:
        assert result == 0, "Tensorflor workload returned non-zero return code"
