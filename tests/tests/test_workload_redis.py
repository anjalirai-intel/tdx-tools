"""
This test module provides the redis workload testing for TDVM
This benchmark test case is designed reference to :
         https://redis.io/topics/benchmarks
"""
import os
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD
from pycloudstack.vmguest import VirshSSH

__author__ = 'cpio'

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_name("bat-redis-td-centos8"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
    pytest.mark.vm_image("latest-guest-image"),
]


def test_tdvm_redis(vm_factory):
    """
    Run redis benchmark test
    Ref: https://redis.io/topics/benchmarks

    Use official docker images redis:latest
    Test Steps:
    1. start VM
    2. Run remote command "systemctl status docker" to check docker service's status
    3. Run remote command "systemctl start docker" to force start docker service
    4. Run remote command "/root/bat-script/redis-bench.sh"
       to launch redis container and  benchmark testing
    """
    LOG.info("Create TD guest to run redis benchmark")
    td_inst = vm_factory.new_vm(VM_TYPE_TD)

    qm = VirshSSH(td_inst)
    qm.put(os.path.join(CURR_DIR, "redis-bench.sh"), "/root/redis-bench.sh")

    # create and start VM instance
    td_inst.create()
    td_inst.start()

    command_list = [
        'systemctl start docker',
        '/root/redis-bench.sh -t get,set'
    ]

    for cmd in command_list:
        LOG.debug(cmd)
        stdout, stderr = qm.check_exec(cmd)
        LOG.debug(stdout)
    qm.close()
