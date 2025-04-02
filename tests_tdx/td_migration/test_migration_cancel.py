"""
Migration cancel for single host td-migration test
The tests includes the following scenarios:
1. Single TD migration, 1 migTD:1 userTD, cancel migration
2. Two userTD migration in parallel, 1 migTD:2 userTD, cancel migration for userTD1 and let migration complete for userTD2
3. Migration cancel and re-migrate

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
MYSQL_LOOP = '40'

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-test-image"),    # from artifacts.yaml
]


def test_td_migration_cancel(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Basic functional test for cancel td-migration

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source and dest TDVM
    couple_tds = create_couple_tds(vm_factory, migtds, incoming_port="6666")

    # pre-migration
    kill_socat_connect()
    socat_runner = create_socat_connect()
    time.sleep(6)
    couple_tds[0].vmm.pre_migration(1234)
    couple_tds[1].vmm.pre_migration(1235)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # start td-migration
    couple_tds[0].vmm.migrate(port="6666")

    # Cancel migration
    cmdret = couple_tds[1].vmm.cancel_migration()
    assert cmdret['return'] == {}, "Migration cancel failed"

    # Run ltp_mm on srcTD
    cmd = "/opt/ltp/runltp -f mm"
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to run ltp_mm on src TD"

    # clean up
    for td in migtds+couple_tds:
        td.destroy()

    socat_runner.terminate()

def test_td_cancel_single_migtd_multi_td(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Multiple TDs intra-host live migration with single MigTD via QEMU
    Cancel one userTD migration and let others complete

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source and dest TDVM
    couple_td0 = create_couple_tds(vm_factory, migtds, incoming_port="6666")
    couple_td1 = create_couple_tds(vm_factory, migtds, incoming_port="5555")
    src_tds = [couple_td0[0], couple_td1[0]]
    dst_tds = [couple_td0[1], couple_td1[1]]

    # pre-migration for tdvms
    kill_socat_connect()
    socat_runner1 = create_socat_connect(tcp_port=9008, vsock=1234)
    socat_runner2 = create_socat_connect(tcp_port=9009, vsock=1236)
    time.sleep(6)
    src_tds[0].vmm.pre_migration(1234)
    dst_tds[0].vmm.pre_migration(1235)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed for src TD1. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed for dst TD1. No pre-migration is done in dmesg."

    src_tds[1].vmm.pre_migration(1236)
    dst_tds[1].vmm.pre_migration(1237)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed for src TD2. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed for dst TD2. No pre-migration is done in dmesg."

    # start td-migration
    src_tds[0].vmm.migrate(port="6666")
    src_tds[1].vmm.migrate(port="5555")

    # run mysql workload on the 2nd userTD during td-migration
    cmd = "/root/workload-test.sh -r " + MYSQL_LOOP
    runner1 = src_tds[1].ssh_run(cmd.split(), vm_ssh_key)
    assert runner1.retcode == 0, "Failed to execute remote command"
    time.sleep(20)

    # Cancel migration of the 1st userTD
    cmdret = src_tds[1].vmm.cancel_migration()
    assert cmdret['return'] == {}, "Migration cancel failed"

    # Check whether TD migration is done for the 2nd userTD
    # Check migration is done from qmp migration status
    assert src_tds[1].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time for srcTD2 is %d" % src_tds[1].vmm.wait_for_migrate_done()[1])

    # Check migration is done from dmesg message
    assert check_migration(dst_tds[1].name), "Migration failed. No migration flow is done in dmesg."

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner1 = src_tds[1].ssh_run(cmd.split(), vm_ssh_key)
    assert runner1.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # Run ltp_mm on srcTD1 and dstTD2
    cmd = "/opt/ltp/runltp -f mm"
    runner = src_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to run ltp_mm on srcTD1"
    runner1 = src_tds[1].ssh_run(cmd.split(), vm_ssh_key)
    assert runner1.retcode == 0, "Failed to run ltp_mm on dstTD2" 

    for td in migtds+src_tds+dst_tds:
        td.destroy()

    socat_runner1.terminate()
    socat_runner2.terminate()

def test_td_migration_remigrate(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Basic functional test for cancel td-migration and re-migrate

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source and dest TDVM
    couple_tds = create_couple_tds(vm_factory, migtds, incoming_port="6666")

    # pre-migration
    kill_socat_connect()
    socat_runner = create_socat_connect()
    time.sleep(6)
    couple_tds[0].vmm.pre_migration(1234)
    couple_tds[1].vmm.pre_migration(1235)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # start td-migration
    couple_tds[0].vmm.migrate(port="6666")

    # Cancel migration
    cmdret = couple_tds[1].vmm.cancel_migration()
    assert cmdret['return'] == {}, "Migration cancel failed"

    # Re-migrate: Pre-migration and then migration again
    kill_socat_connect()
    socat_runner = create_socat_connect()
    time.sleep(6)
    couple_tds[0].vmm.pre_migration(1234)
    couple_tds[1].vmm.pre_migration(1235)
    time.sleep(3)     

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # start td-migration
    couple_tds[0].vmm.migrate(port="6666")

    # Wait for migration complete
    assert couple_tds[0].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time is %d" % couple_tds[0].vmm.wait_for_migrate_done()[1])

    # Check migration is done from dmesg message
    assert check_migration(couple_tds[1].name), "Migration failed. No migration flow is done in dmesg."

    # Run ltp_mm on dst userTD
    cmd = "/opt/ltp/runltp -f mm"
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to run ltp_mm on dst TD"

    # clean up
    for td in migtds+couple_tds:
        td.destroy()

    socat_runner.terminate()
