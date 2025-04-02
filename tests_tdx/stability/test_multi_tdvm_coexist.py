"""
Stability testing for multiple TDVMs, EFI VMs, and legacy VMs.
"""
import os
import time
import threading
import logging
import pytest

from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI, VM_TYPE_LEGACY, \
    VM_STATE_RUNNING, VM_STATE_PAUSE, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

_NUM_TD_GUEST = 25
_NUM_EFI_GUEST = 5
_NUM_LEGACY_GUEST = 5

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


_WORKLOAD_NGINX = [
    'sysctl -w net.ipv6.conf.all.disable_ipv6=1',
    'systemctl start nginx',
    'siege -q -r 25000 -b localhost',
    'systemctl stop nginx',
    'sysctl -w net.ipv6.conf.all.disable_ipv6=0',
    'rm -f /var/log/nginx/access.log',
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
    '/root/y-cruncher/y-cruncher skip-warnings bench 250m',
    'rm -f /root/Pi*',
]

_WORKLOADS = [
    _WORKLOAD_NGINX,
    _WORKLOAD_REDIS,
    _WORKLOAD_TF,
    _WORKLOAD_YCRUNCHER,
]


@pytest.fixture(scope="module")
def multi_vm_instances(vm_factory, vm_ssh_pubkey):
    """
    Guest instance fixture
    """
    started_instances = []

    vmspec = VMSpec.model_base()
    vmspec.memsize = 3 * 1024 * 1024

    for index in range(_NUM_TD_GUEST):
        LOG.info("Creating %d TD VM", index)
        vm_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=vmspec)
        vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
        vm_inst.create()
        vm_inst.start()
        started_instances.append(vm_inst)

    for index in range(_NUM_EFI_GUEST):
        LOG.info("Creating %d EFI VM", index)
        vm_inst = vm_factory.new_vm(VM_TYPE_EFI, vmspec=vmspec)
        vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
        vm_inst.create()
        vm_inst.start()
        started_instances.append(vm_inst)

    for index in range(_NUM_LEGACY_GUEST):
        LOG.info("Creating %d legacy VM", index)
        vm_inst = vm_factory.new_vm(VM_TYPE_LEGACY, vmspec=vmspec)
        vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
        vm_inst.create()
        vm_inst.start()
        started_instances.append(vm_inst)

    for item in vm_factory.vms.values():
        item.wait_for_ssh_ready()

    return started_instances


def worker(instance, vm_ssh_key, index, results):
    """
    The worker to launch workload for each guest in parallel:

    1. suspended for 5 seconds
    2. resume
    3. run workload based on index

    """

    LOG.info("Suspend %s guest", instance.vmtype)
    instance.suspend()
    ret = instance.wait_for_state(VM_STATE_PAUSE)
    assert ret, "Suspend timeout"

    time.sleep(5)

    LOG.info("Resume %s guest", instance.vmtype)
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
def test_multi_tdvm_coexist(multi_vm_instances, vm_ssh_key):
    """
    Test the basic lifecycle of multiple guests: virsh suspend/resume with workload

    Step 1: Create multiple guests: 25 TD, 5 EFI, 5 Legacy
    Step 2: suspend TD guests for 5 seconds
    Step 3: resume TD guests
    Step 4: run workload
    Step 5: repeat step 2 ~ step 4 for cycling

    NOTE: vm_factory will cleanup all created VM instance in its __del__ later,
          so do not clean them explicitly.
    """

    jobs = []
    results = [-1] * (_NUM_TD_GUEST + _NUM_EFI_GUEST + _NUM_LEGACY_GUEST)
    for index in range(len(multi_vm_instances)):
        td_job = threading.Thread(target=worker, args=(multi_vm_instances[index], vm_ssh_key, index, results))
        jobs.append(td_job)
        td_job.start()

    for job in jobs:
        job.join()

    for result in results:
        assert result == 0, "Workload returned non-zero return code"
