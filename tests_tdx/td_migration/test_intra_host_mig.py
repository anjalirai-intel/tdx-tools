"""
Do single host td-migration test
The tests includes the following scenarios:
1. Single TD migration, 1 migTD:1 userTD
2. Single TD migration, 1 migTD:1 userTD, migTD is killed before live migration
3. Two userTD migration in parallel, 1 migTD:2 userTD
4. Two userTD migration in parallel, 1 migTD:1 userTD
5. Single TD migration, 1 migTD:1 userTD with configurable tsx/tsc/mwait for userTD
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


@pytest.mark.bat
def test_td_migration(vm_factory, vm_ssh_key):
    """
    Basic functional test for td-migration

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

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # clean up
    for td in migtds+couple_tds:
        td.destroy()

    socat_runner.terminate()

def test_td_migration_prekill_migtd(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    TD-migration with single MigTD via QEMU, kill migTD before migration finishing

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

    # kill migtd after pre-migration
    for migtd in migtds:
        migtd.destroy()

    # start td-migration
    couple_tds[0].vmm.migrate(port="6666")

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

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # clean up
    for td in couple_tds:
        td.destroy()

    socat_runner.terminate()

def test_td_migration_single_migtd_multi_td(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Multiple TDs intra-host live migration with single MigTD via QEMU

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
    assert check_pre_mig(migtds[0].pid), "Pre-migration for srcTD1 failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration for dstTD1 failed. No pre-migration is done in dmesg."

    src_tds[1].vmm.pre_migration(1236)
    dst_tds[1].vmm.pre_migration(1237)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration for srcTD2 failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration for dstTD2 failed. No pre-migration is done in dmesg."

    # start td-migration
    src_tds[0].vmm.migrate(port="6666")
    src_tds[1].vmm.migrate(port="5555")

    # run mysql workload during td-migration
    cmd = "/root/workload-test.sh -r " + MYSQL_LOOP
    runner = src_tds[0].ssh_run(cmd.split(), vm_ssh_key, no_wait=True)
    runner1 = src_tds[1].ssh_run(cmd.split(), vm_ssh_key)
    assert runner1.retcode == 0, "Failed to execute remote command"
    time.sleep(20)

    # Check whether TD migration is done
    # Check migration is done from qmp migration status
    assert src_tds[0].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."
    assert src_tds[1].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time for srcTD1 is %d" % src_tds[0].vmm.wait_for_migrate_done()[1])
    LOG.info("Total migration time for srcTD2 is %d" % src_tds[1].vmm.wait_for_migrate_done()[1])

    # Check migration is done from dmesg message
    assert check_migration(dst_tds[0].name), "Migration failed. No migration flow is done in dmesg."
    assert check_migration(dst_tds[1].name), "Migration failed. No migration flow is done in dmesg."

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = src_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"
    runner1 = src_tds[1].ssh_run(cmd.split(), vm_ssh_key)
    assert runner1.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    for td in migtds+src_tds+dst_tds:
        td.destroy()

    socat_runner1.terminate()
    socat_runner2.terminate()

def test_td_migration_multi_migtd_multi_td(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Multiple TDs intra-host live migration with multiple MigTDs via QEMU

    """
    # start two migtds
    migtds_group0 = create_couple_migtds(vm_factory)
    migtds_group1 = create_couple_migtds(vm_factory)

    # create source and dest TDVM
    couple_td0 = create_couple_tds(vm_factory, migtds_group0, incoming_port="6666")
    couple_td1 = create_couple_tds(vm_factory, migtds_group1, incoming_port="5555")
    src_tds = [couple_td0[0], couple_td1[0]]
    dst_tds = [couple_td0[1], couple_td1[1]]

    # pre-migration for tdvms
    kill_socat_connect()
    socat_runner1 = create_socat_connect(tcp_port=9008, vsock=1234)
    socat_runner2 = create_socat_connect(tcp_port=9009, vsock=1236)
    time.sleep(6)
    src_tds[0].vmm.pre_migration(1234)
    dst_tds[0].vmm.pre_migration(1235)
    src_tds[1].vmm.pre_migration(1236)
    dst_tds[1].vmm.pre_migration(1237)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds_group0[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds_group0[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    assert check_pre_mig(migtds_group1[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds_group1[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # start td-migration
    src_tds[0].vmm.migrate(port="6666")
    src_tds[1].vmm.migrate(port="5555")

    # run mysql workload during td-migration
    cmd = "/root/workload-test.sh -r " + MYSQL_LOOP
    runner = src_tds[0].ssh_run(cmd.split(), vm_ssh_key, no_wait=True)
    runner1 = src_tds[1].ssh_run(cmd.split(), vm_ssh_key)
    assert runner1.retcode == 0, "Failed to execute remote command"
    time.sleep(20)

    # Check whether TD migration is done
    # Check migration is done from qmp migration status
    assert src_tds[0].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."
    assert src_tds[1].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time for srcTD1 is %d" % src_tds[0].vmm.wait_for_migrate_done()[1])
    LOG.info("Total migration time for srcTD2 is %d" % src_tds[1].vmm.wait_for_migrate_done()[1])

    # Check migration is done from dmesg message
    assert check_migration(dst_tds[0].name), "Migration failed. No migration flow is done in dmesg."
    assert check_migration(dst_tds[1].name), "Migration failed. No migration flow is done in dmesg."

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = src_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"
    runner1 = src_tds[1].ssh_run(cmd.split(), vm_ssh_key)
    assert runner1.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # Run ltp_mm on destTD
    cmd = "/opt/ltp/runltp -f mm"
    runner = src_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to run ltp_mm on dstTD1"
    runner1 = src_tds[1].ssh_run(cmd.split(), vm_ssh_key)
    assert runner1.retcode == 0, "Failed to run ltp_mm on dstTD2" 

    for td in migtds_group0+migtds_group1+src_tds+dst_tds:
        td.destroy()

    socat_runner1.terminate()
    socat_runner2.terminate()

testdata = [
    (False, False, None),
    (False, False, "on"),
    (False, False, "off"),
]

@pytest.mark.parametrize("tsx, tsc, mwait", testdata)
def test_td_migration_tsx_tsc_mwait(vm_factory, vm_ssh_key, tsx, tsc, mwait):
    """
    Basic functional test for td-migration with TSX/TSC/MWAIT as follows:
    1. tsx disabled, tsc_deadline timer disabled, mwait by default
    2. tsx disabled, tsc_deadline disabled, mwait on
    3. tsx disabled, tsc_deadline disabled, mwait off

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source and dest TDVM
    couple_tds = create_couple_tds(vm_factory, migtds, incoming_port="6666", tsx=tsx, tsc=tsc, mwait=mwait)

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

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # clean up
    for td in migtds+couple_tds:
        td.destroy()

    socat_runner.terminate()
