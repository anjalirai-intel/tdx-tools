"""
Check if amber-cli can get quote successfully
...
"""
import os
import datetime
import logging
import pytest

__author__ = "cpio"

LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


@pytest.mark.kubevirt
def test_amber_get_quote(vm_ssh_key, kubevirt_tdvm):
    """
    Test if amber-cli can get quote in TD guest
    """

    # start tdvm in kubevirt
    kubevirt_tdvm.create()
    kubevirt_tdvm.start()
    kubevirt_tdvm.wait_for_ssh_ready()

    command = "amber-cli quote"

    ssh_runner = kubevirt_tdvm.ssh_run(command.split(), vm_ssh_key)

    kubevirt_tdvm.shutdown()
    kubevirt_tdvm.destroy()

    assert ssh_runner.retcode == 0, "Failed to execute ssh command"
    LOG.info(ssh_runner.stdout[0])
