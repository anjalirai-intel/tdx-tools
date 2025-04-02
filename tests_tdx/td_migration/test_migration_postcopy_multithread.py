"""
Post copy test for single host td-migration test
The tests includes the following scenarios:
1. Run memory intensive workload and trigger post copy
2. Pre-binding + post copy + multi thread
"""
import os
import logging
import datetime
import time
import pytest

from pycloudstack.cmdrunner import NativeCmdRunner
from migration_utils import *

__author__ = 'cpio'


LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
MYSQL_LOOP = '20'
MIG_HASH = "d83d9a38c238ef3b7bc207bbea3287a8b37b37e731480a8d240d2a6953086c5ecbdf7ee4c72fec3a3e9d4a87f4f9b4fe"

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-test-image"),    # from artifacts.yaml
]


def test_td_migration_post_copy(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Post copy

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create user TDs
    couple_tds = create_couple_tds(vm_factory, migtds, incoming_port="6666")

    # pre-migration
    socat_runner = create_socat_connect()
    time.sleep(6)
    # src userTD will bind with migtd before pre-migration
    couple_tds[0].vmm.pre_migration(1234)
    couple_tds[1].vmm.pre_migration(1235)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # Set post copy on
    capability_list = [{"capability":"postcopy-ram", "state": True},
    {"capability":"postcopy-preempt", "state": True}]

    couple_tds[0].vmm.set_migration_capability(capability_list)
    couple_tds[1].vmm.set_migration_capability(capability_list)

    # start td-migration
    couple_tds[0].vmm.migrate(port="6666")
    time.sleep(2)

    # start td-migration post copy
    couple_tds[0].vmm.migrate_postcopy()

    # query migration capabilities to check post copy capability
    mig_cap = couple_tds[0].vmm.get_migration_capability()

    # run mysql workload during td-migration
    cmd = "/root/workload-test.sh -r " + MYSQL_LOOP
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # Check whether TD migration is done
    # Check migration is done from qmp migration status
    assert couple_tds[0].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time is %d" % couple_tds[0].vmm.wait_for_migrate_done()[1])

    # Check migration is done from dmesg message
    assert check_migration(couple_tds[1].name), "Migration failed. No migration flow is done in dmesg."

    # Run ltp_mm on destTD
    cmd = "/opt/ltp/runltp -f mm"
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to run ltp_mm on dstTD"

    # clean up
    for td in migtds+couple_tds:
        td.destroy()

    socat_runner.terminate()

def test_td_migration_multi_thread(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Multi thread TD migration

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create user TDs
    couple_tds = create_couple_tds(vm_factory, migtds, incoming_port="8888")

    # pre-migration
    socat_runner = create_socat_connect(vsock=1556)
    time.sleep(6)

    # src userTD will bind with migtd before pre-migration
    couple_tds[0].vmm.pre_migration(value=1556)
    couple_tds[1].vmm.pre_migration(value=1557)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # Set multi thread capabilities
    capability_list = [{"capability":"multifd", "state": True}]
    parameter_list = [{"multifd-channels": 4}]

    couple_tds[0].vmm.set_migration_capability(capability_list)
    couple_tds[0].vmm.set_migration_parameters(parameter_list)

    couple_tds[1].vmm.set_migration_capability(capability_list)
    couple_tds[1].vmm.set_migration_parameters(parameter_list)

    # start td-migration
    couple_tds[0].vmm.migrate(port="8888")

    # run mysql workload during td-migration
    cmd = "/root/workload-test.sh -r " + MYSQL_LOOP
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # Check whether TD migration is done
    # Check migration is done from qmp migration status
    assert couple_tds[0].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time is %d" % couple_tds[0].vmm.wait_for_migrate_done()[1])

    # Check migration is done from dmesg message
    assert check_migration(couple_tds[1].name), "Migration failed. No migration flow is done in dmesg."    

    # Run ltp_mm on destTD
    cmd = "/opt/ltp/runltp -f mm"
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to run ltp_mm on dstTD"

    # clean up
    for td in migtds+couple_tds:
        td.destroy()

    socat_runner.terminate()

def test_td_migration_mix(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Pre-binding + Post copy
    Note: Enabling post-copy + multi-streams at the same time is not supported

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source userTD using pre-binding
    src_td = create_usertd(vm_factory, "src", migtds[0], mig_hash=MIG_HASH)

    # create dest userTD binding with migTD directly
    dst_td = create_usertd(vm_factory, "dst", migtds[1], src_td=src_td, incoming_port="7777")

    # pre-migration
    socat_runner = create_socat_connect(vsock="1345")
    time.sleep(6)

    # src userTD will bind with migtd before pre-migration
    src_td.vmm.pre_migration(value=1345, pre_binding=True)
    dst_td.vmm.pre_migration(value=1346)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # Set post copy on
    capability_list = [{"capability":"postcopy-ram", "state": True},
    {"capability":"postcopy-preempt", "state": True}]

    src_td.vmm.set_migration_capability(capability_list)
    dst_td.vmm.set_migration_capability(capability_list)

    # query migration capabilities to check post copy capability
    mig_cap = src_td.vmm.get_migration_capability()

    # start td-migration
    src_td.vmm.migrate(port="7777")
    time.sleep (3)

    # start td-migration post copy
    src_td.vmm.migrate_postcopy()

    # run mysql workload during td-migration
    cmd = "/root/workload-test.sh -r " + MYSQL_LOOP
    runner = src_td.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # Check whether TD migration is done
    # Check migration is done from qmp migration status
    assert src_td.vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time is %d" % src_td.vmm.wait_for_migrate_done()[1])

    # Check migration is done from dmesg message
    assert check_migration(dst_td.name), "Migration failed. No migration flow is done in dmesg."

    # Run ltp_mm on destTD
    cmd = "/opt/ltp/runltp -f mm"
    runner = src_td.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to run ltp_mm on dstTD"

    # clean up
    for td in migtds:
        td.destroy()
    src_td.destroy()
    dst_td.destroy()

    socat_runner.terminate()
