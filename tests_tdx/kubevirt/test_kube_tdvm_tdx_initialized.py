"""
TDX Guest check: to verify TDX guest basic environment:
"""
import datetime
import logging
import pytest

__author__ = "cpio"

LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


@pytest.mark.kubevirt
def test_tdvm_cpu_flags(vm_ssh_key, kubevirt_tdvm):
    """
    check tdx and amx cpu flags if in the TD guest.
    """

    # start tdvm in kubevirt
    kubevirt_tdvm.create()
    kubevirt_tdvm.start()
    kubevirt_tdvm.wait_for_ssh_ready()

    command = "lscpu | grep -i flags"

    ssh_runner = kubevirt_tdvm.ssh_run(command.split(), vm_ssh_key)

    kubevirt_tdvm.shutdown()
    kubevirt_tdvm.destroy()

    assert ssh_runner.retcode == 0, "Failed to execute ssh command"
    LOG.info(ssh_runner.stdout[0])

    flags = ["tdx_guest", "amx_tile", "amx_int8", "amx_bf16"]
    for f in flags:
        assert f in ssh_runner.stdout[0], f"flag {f} not in the guest!"
