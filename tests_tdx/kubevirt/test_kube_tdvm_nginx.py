"""
This test module provides the nginx workload testing for TDVM
This benchmark test case is designed reference to :
         https://www.joedog.org/siege-home/
"""
import os
import datetime
import logging
import pytest

__author__ = "cpio"

CURR_DIR = os.path.dirname(__file__)
LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


@pytest.mark.kubevirt
def test_tdvm_nginx(vm_ssh_key, kubevirt_tdvm):
    """
    Test if can get td-report in TD guest
    """

    # start tdvm in kubevirt
    kubevirt_tdvm.create()
    kubevirt_tdvm.start()
    kubevirt_tdvm.wait_for_ssh_ready()

    # scp nginx-bensh.sh in
    nginx_script = os.path.join(CURR_DIR, "nginx-bench.sh")
    ssh_runner = kubevirt_tdvm.scp_in(nginx_script, "/root/", vm_ssh_key)
    assert ssh_runner.retcode == 0, "Failed to execute ssh command"

    command = "/root/nginx-bench.sh"
    ssh_runner = kubevirt_tdvm.ssh_run(command.split(), vm_ssh_key)

    kubevirt_tdvm.shutdown()
    kubevirt_tdvm.destroy()

    assert ssh_runner.retcode == 0, "Failed to execute ssh command"
    LOG.info(ssh_runner.stdout[0])

