import threading
import logging
import pytest

from pycloudstack.vmparam import VM_TYPE_TD, VM_STATE_RUNNING, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

_MAX_TD_GUEST = 25

_STRESS_DURATION = 12 * 60 * 60  # 12 hours
_TEST_TIMEOUT = 13 * 60 * 60  # 13 hours to account for TD creation time

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

    1. wait for TD to begin running
    2. run stress-ng fault workload

    """

    ret = instance.wait_for_state(VM_STATE_RUNNING)
    assert ret, "running timeout"

    cmd = f"stress-ng --fault 1 --timeout {_STRESS_DURATION}"
    runner = instance.ssh_run(cmd.split(), vm_ssh_key)
    results[index] = runner.retcode


# pylint: disable=W0621
@pytest.mark.timeout(_TEST_TIMEOUT)
def test_multi_tdvm_stress_ng_faults(multi_vm_instances, vm_ssh_key):
    """
    Test TD with fault stressors running
    Step 1: Create multiple TD guests
    Step 2: run workload stress-ng --fault

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
        job.join(_TEST_TIMEOUT)

    for result in results:
        assert result == 0, "stress-ng returned non-zero return code"
