"""
This test module check workload running on user TD which has vTPM device
"""

import logging
import os
import pytest

from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import VM_TYPE_TD, VM_STATE_RUNNING

LOG = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-test-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]

def test_vtpm_workload_nginx(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run nginx workload on the user TD
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "../workload/nginx-bench.sh"), "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to check connectivity between user TD and vTPM TD
    # Encrypt and decrypt some data
    cmd = "tpm2_pcrread"
    LOG.debug(cmd)
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # Run nginx workload in the user TD
    cmd = 'sysctl -w net.ipv6.conf.all.disable_ipv6=1'
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)

    command_list = [
        'systemctl start docker',
        '/root/nginx-bench.sh'
    ]
    for cmd in command_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"

def test_vtpm_workload_redis(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    1. Create TDVM with vTPM device - vTPM TD and user TD should be running
    2. Run redis workload on the user TD
    """
    
    LOG.info("Create TDVM with vTPM device")

    td_inst = vm_factory.new_vm(VM_TYPE_TD, has_vtpm=True)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.image.copy_in(
        os.path.join(CURR_DIR, "../workload/redis-bench.sh"), "/root/")

    # create and start VM instance
    td_inst.create()
    td_inst.start()

    # Check both user TD and vTPM TD are running
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"
    vtpm_dom, vtpm_id = td_inst.get_vtpm_td_dom()
    assert td_inst.vtpm_state() == VM_STATE_RUNNING, "vTPM TD is not running"

    # Run tpm command to check connectivity between user TD and vTPM TD
    cmd = "tpm2_pcrread"
    LOG.debug(cmd)
    runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # Run redis workload in the user TD
    command_list = [
        'systemctl start docker',
        '/root/redis-bench.sh -t get,set'
    ]
    for cmd in command_list:
        LOG.debug(cmd)
        runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
        assert runner.retcode == 0, "Failed to execute remote command"
