"""
General functions for td migration test cases
"""
import os
import logging
import time
from gpl.vmmqmp import VMMQemu
from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_MIGTD, VMSpec

CURR_DIR = os.path.dirname(__file__)

def create_socat_connect(tcp_port=9011, vsock=1234):
    """
    Create socat connection for pre-migration
    """
    file_path = os.path.join(CURR_DIR, "socat-connection.sh")
    socat_runner = NativeCmdRunner(cmdarr=[file_path, "-t", f"{tcp_port}", "-v", f"{vsock}"])
    socat_runner.runnowait()

    return socat_runner

def kill_socat_connect():
    """
    Kill any existing socat connection
    """
    cmd = "killall -r socat"
    runner = NativeCmdRunner(cmd.split())
    runner.runwait()

def create_couple_migtds(vm_factory):
    """
    Create a couple of migtds for td-migration
    """
    src_migtd = vm_factory.new_vm(VM_TYPE_MIGTD, vmspec=VMSpec.model_migtd(), vm_class=VMMQemu,
                                  auto_start=False)
    src_migtd.create(stop_at_begining=False)
    dst_migtd = vm_factory.new_vm(VM_TYPE_MIGTD, vmspec=VMSpec.model_migtd(), vm_class=VMMQemu,
                                  auto_start=False)
    dst_migtd.create(stop_at_begining=False)

    # wait migtd to start
    time.sleep(10)

    return [src_migtd, dst_migtd]


def create_couple_tds(vm_factory, migtds, incoming_port="6666", tsx=None, tsc=None, mwait=None, mig_hash=None):
    """
    Create a couple of user tds(srcTD, dstTD) for td-migration
    """
    # create source and dest TDVM
    src_td = vm_factory.new_vm(VM_TYPE_TD, vmspec=VMSpec.model_base(), vm_class=VMMQemu, auto_start=False, migtd_pid=migtds[0].pid, tsx=tsx, tsc=tsc, mwait=mwait, mig_hash=mig_hash, mac_addr="00:16:3e:68:36:7f")

    src_td.image.copy_in(os.path.join(CURR_DIR, "workload-test.sh"), "/root/")
    src_td.create(stop_at_begining=False)

    # add incoming port for dstTD
    dst_td = vm_factory.new_vm(VM_TYPE_TD, disk_img=src_td.image, vmspec=VMSpec.model_base(), vm_class=VMMQemu, auto_start=False, migtd_pid=migtds[1].pid, incoming_port=incoming_port, tsx=tsx, tsc=tsc, mwait=mwait, mig_hash=mig_hash, mac_addr="00:16:3e:68:36:7f")

    dst_td.create(stop_at_begining=False)

    assert src_td.wait_for_ssh_ready()

    return [src_td, dst_td]

def create_usertd(vm_factory, td_type, migtd, incoming_port="6666", tsx=None, tsc=None, mwait=None, mig_hash=None, src_td=None):
    """
    Create a user TD for td-migration
    """
    if td_type == "src":
        # create source user TD
        src_td = vm_factory.new_vm(VM_TYPE_TD, vmspec=VMSpec.model_base(), vm_class=VMMQemu, auto_start=False, migtd_pid=migtd.pid, tsx=tsx, tsc=tsc, mwait=mwait, mig_hash=mig_hash)

        src_td.image.copy_in(os.path.join(CURR_DIR, "workload-test.sh"), "/root/")
        src_td.create(stop_at_begining=False)
        assert src_td.wait_for_ssh_ready()
        return src_td
    elif td_type == "dst":
        # create destination user TD with incoming port
        assert src_td is not None, "Cannot get src TD image to create dst TD"
        dst_td = vm_factory.new_vm(VM_TYPE_TD, disk_img=src_td.image, vmspec=VMSpec.model_base(), vm_class=VMMQemu, auto_start=False, migtd_pid=migtd.pid, incoming_port=incoming_port, tsx=tsx, tsc=tsc, mwait=mwait, mig_hash=mig_hash)

        dst_td.create(stop_at_begining=False)
        return dst_td
    else:
        raise NotImplementedError

def check_msg(keyword, pid):
    """
    Check whether dmesg contains keyword and pid
    """
    cmd = "dmesg"
    msg_runner = NativeCmdRunner(cmd.split())
    msg_runner.runwait()

    is_complete = False
    results = msg_runner.stdout
    for result in results:
        if keyword in result and str(pid) in result:
            is_complete = True
            break

    return is_complete

def check_pre_mig(migtd_pid):
    """
    Check whether dmesg contains pre-migration is done
    """
    return check_msg("Pre-migration is done", migtd_pid)

def check_migration(td_name):
    """
    Check whether dmesg contains migration flow is done
    """
    cmd = "pgrep -f " + td_name
    msg_runner = NativeCmdRunner(cmd.split())
    msg_runner.runwait()
    
    dst_td_pid = msg_runner.stdout[0]
    return check_msg("migration flow is done", dst_td_pid)     
