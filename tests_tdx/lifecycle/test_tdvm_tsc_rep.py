"""
TDX Guest check: to verify TDX guest basic environment:
1. TDX initialized (dmesg)
2. TSC clock source
3. TSC frequency
...
"""
import os
import datetime
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VMSpec

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# pylint: disable=invalid-name,redefined-outer-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-image"),    # from artifacts.yaml
]


@pytest.fixture(scope="function")
def base_td_guest_inst(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    """
    Create and start a td guest instance
    """
    td_inst = vm_factory.new_vm(VM_TYPE_TD, vmspec=VMSpec.model_large())
    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.create()
    td_inst.start()
    td_inst.wait_for_ssh_ready()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    yield td_inst

    td_inst.destroy()


def _remote_run_and_fetch(td_inst, vm_ssh_key, output, command, output_file):
    """
    Runs a command in TD guest and then scp_out the result

    The result is fetched to host and the caller will do further check
    on the result, though the "further check" can also take place in guest.
    One of the reason to fetch the result to host is to save the original output
    and upload to log server for manual analysis in case needed.
    """
    runner = td_inst.ssh_run(command.split(), vm_ssh_key)
    assert runner.retcode == 0, "failed to execute remote command"

    runner = td_inst.scp_out(
        os.path.join('/tmp', output_file), output, vm_ssh_key)
    assert runner.retcode == 0, "failed to copy-out result file"


@pytest.mark.repeat(50)
def test_tdvm_clocksource_tsc_repeatedly(base_td_guest_inst, vm_ssh_key, output):
    """
    check clocksource is *tsc* in TD guest.

    1. remotely run *cat /sys/devices/system/clocksource/clocksource0/current_clocksource*
    2. copy result from td guest to local dir
    3. compare the clocksource name with *tsc*
    """
    LOG.info("Test if clocksource is tsc in TD guest")

    output_file = f"tdx_clocksource_check_{DATE_SUFFIX}.log"
    command = f"cat /sys/devices/system/clocksource/clocksource0/current_clocksource\
                > /tmp/{output_file}"

    _remote_run_and_fetch(base_td_guest_inst, vm_ssh_key, output, command, output_file)

    saved_file = os.path.join(output, output_file)
    with open(saved_file, 'r', encoding="utf8") as fsaved:
        assert fsaved.read().strip() == "tsc"
        LOG.info("TD guest clocksource is tsc")
