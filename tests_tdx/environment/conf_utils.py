"""
TDX Guest configuration utils
"""
import logging
from pycloudstack.vmparam import VM_TYPE_TD

__author__ = 'cpio'

LOG = logging.getLogger(__name__)


def get_td_vm(vm_factory, vm_ssh_key, vm_ssh_pubkey, tsc_opt=None, tsx_opt=None, mwait_opt=None):
    """
    Create and start a td guest instance
    """
    params = f"tsc_opt={tsc_opt}, tsx_opt={tsx_opt}, mwait_opt={mwait_opt}"
    LOG.info(params)
    td_inst = vm_factory.new_vm(VM_TYPE_TD, tsc=tsc_opt, tsx=tsx_opt, mwait=mwait_opt)
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    # Install the prerequisite tools. If it's already installed, the install will also
    # return 0 to indicate success.
    cmdret, _, cmderr = td_vm_exe(td_inst, vm_ssh_key, "modprobe msr")
    assert cmdret == 0, f"modprobe msr fail {cmderr}"
    cmdret, _, cmderr = td_vm_exe(td_inst, vm_ssh_key, "apt install -y msr-tools")
    assert cmdret == 0, f"apt install msr-tools fail {cmderr}"
    cmdret, _, cmderr = td_vm_exe(td_inst, vm_ssh_key, "apt install -y cpuid")
    assert cmdret == 0, f"apt install cpuid fail {cmderr}"

    # return the TDVM for test
    yield td_inst

    # release resources for tear down
    td_inst.destroy()


def td_vm_exe(td_inst, vm_ssh_key, command):
    """
    Runs a command in TD guest and return the stdout
    """
    runner = td_inst.ssh_run(command.split(), vm_ssh_key)
    outstr=""
    if len(runner.stdout) > 0:
        outstr = runner.stdout[0]
        LOG.info(outstr)
    errstr=""
    if len(runner.stderr) > 0:
        errstr = runner.stderr[0]
        LOG.info(errstr)
    retcode = runner.retcode
    return retcode, outstr, errstr


def get_cpuid_info(td_inst, vm_ssh_key, leaf, register, subleaf="0"):
    """
    Get cpuid info for given leaf and register by parsing the command line stdout of cpuid.
    """
    cmd = f"cpuid -1 -r -l {leaf} -s {subleaf} | grep {register} | sed 's/.* {register}" + r"=\([^ ]*\) .*/\1/g'"
    LOG.info("get cpuid info: %s", cmd)
    cmdret, cmdout, cmderr = td_vm_exe(td_inst, vm_ssh_key, cmd)
    assert cmdret == 0, f"cpuid fail {cmderr}"
    register_value=int(cmdout, 16)
    return register_value


def get_msr_info(td_inst, vm_ssh_key, msr):
    """
    Get msr info
    """
    cmdret, cmdout, cmderr = td_vm_exe(td_inst, vm_ssh_key, f"rdmsr {msr}")
    if cmdret == 0:
        return cmdout
    LOG.info("rdmsr error %s", cmderr)
    return None
