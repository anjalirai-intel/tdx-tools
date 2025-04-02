"""
Test network functionality within TD guest
"""

import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD
from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmguest import VirshSSH

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_image("latest-guest-image"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
]


def test_tdvm_wget(vm_factory):
    """
    Test wget functionality within TD guest, the network could be NAT, bridget.
    """
    LOG.info("Create TD guest")
    vm_inst = vm_factory.new_vm(VM_TYPE_TD)

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()

    qm = VirshSSH(vm_inst)
    c_out, c_err = qm.check_exec("wget https://www.baidu.com/")
    LOG.info("%s", c_out)
    qm.close()


def test_tdvm_ssh_forward(vm_factory):
    """
    Test SSH forward functionality within TD guest
    """
    LOG.info("Create TD guest")
    inst = vm_factory.new_vm(VM_TYPE_TD)

    # create and start VM instance
    inst.create()
    inst.start()

    qm = VirshSSH(inst)
    c_out, c_err = qm.check_exec("ls /")
    LOG.info("%s", c_out)
    qm.close()


def test_tdvm_bridge_network_ip(vm_factory):
    """
    Test wget functionality within TD guest, the network could be NAT, bridget.
    """
    LOG.info("Create TD guest")
    vm_inst = vm_factory.new_vm(VM_TYPE_TD)

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()

    vm_bridge_ip = vm_inst.get_ip()
    assert vm_bridge_ip is not None

    runner = NativeCmdRunner(["ping", "-c", "3", vm_bridge_ip])
    runner.runwait()
    assert runner.retcode == 0
