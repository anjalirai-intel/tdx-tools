"""
Stability testings for multiple TD guests cycling includes:
- virsh create/destroy

"""
import logging
import pytest
import threading
import uuid
from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmimg import VMImage
from pycloudstack.vmguest import VMGuest, VMMLibvirt
from pycloudstack.vmparam import VM_TYPE_TD, VM_STATE_RUNNING, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

_MAX_TD_GUEST = 25

_TD_MUTEX = threading.Lock()

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

vmspec = VMSpec.model_base()
vmspec.cores = 8
vmspec.memsize = 32 * 1024 * 1024


def worker(base_image, kernel, index, results):
    vm_id = str(uuid.uuid4())
    vm_name = f"td-{vm_id}"
    image = VMImage(base_image).clone(vm_name + ".qcow2")
    guest_distro = "ubuntu"
    _TD_MUTEX.acquire()
    vm_inst = VMGuest(vm_name, image, guest_distro=guest_distro, vmid=vm_id, vmtype=VM_TYPE_TD, vmspec=vmspec, kernel=kernel,
                      vmm_class=VMMLibvirt, io_mode="native", cache="none")
    LOG.info("Create index %d TD", index)
    try:
        vm_inst.create()
        vm_inst.start()
    except Exception:
        LOG.warning("TD creation failed at index %d, name %s", index, vm_name)
        vm_inst.destroy()
        return
    finally:
        _TD_MUTEX.release()

    vm_inst.wait_for_state(VM_STATE_RUNNING)
    results[index] = vm_inst.wait_for_ssh_ready()
    if results[index]:
        vm_inst.destroy(delete_image=True, delete_log=True)
    else:
        LOG.warning("Could not ssh to td %s", vm_name)


@pytest.mark.repeat(1000)
def test_multi_tdvm_create_destroy(vm_image, vm_kernel):
    """
    Test multiple TD guests create/destory.

    Step 1. Create 25 instances of TD guest
    Step 2. Destroy each TD guest
    Step 3: repeat step 1 and step 2 by 1000 cycles for Alpha
    DPMO <= 2000
       1 defects / ( 10 TD guest * 50 cycles ) * 1000000 = 2000 DPMO

    """
    jobs = []
    results = [False] * _MAX_TD_GUEST

    # HACK: workaround to libvirt failure after 163 cycles
    runner = NativeCmdRunner(["systemctl", "restart", "libvirtd.service"])
    assert runner.runwait() == 0

    for index in range(_MAX_TD_GUEST):
        td_job = threading.Thread(target=worker, args=(vm_image, vm_kernel, index, results))
        jobs.append(td_job)
        td_job.start()

    for index in range(_MAX_TD_GUEST):
        jobs[index].join()

    for index in range(_MAX_TD_GUEST):
        if not results[index]:
            LOG.error("SSH to TD %d failed", index)
            assert False
