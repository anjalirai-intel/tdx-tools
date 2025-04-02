"""
Pre-binding test for single host td-migration test
The tests includes the following scenarios:
1. Source user TD use pre-binding and dst userTD binds migTD when created. Bind src migTD with src userTD before pre-migration
2. Dst user TD use pre-binding and src userTD binds migTD when created. Bind dst migTD with dst userTD before pre-migration
3. Both src and dst user TD use pre-binding
4. Mix scenario - One pair of userTDs use pre-binding and another pair does not. The 2 pairs bind with the same migTD pair. Migrate the 2 src userTDs in parallel.
"""
import os
import logging
import datetime
import time
import hashlib
import pytest

from pycloudstack.cmdrunner import NativeCmdRunner
from migration_utils import *

__author__ = 'cpio'


LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
MYSQL_LOOP = '40'
MIG_HASH = "d83d9a38c238ef3b7bc207bbea3287a8b37b37e731480a8d240d2a6953086c5ecbdf7ee4c72fec3a3e9d4a87f4f9b4fe"

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-test-image"),    # from artifacts.yaml
]


def test_td_migration_src_pre_binding(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Source user TD uses pre-binding

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source userTD using pre-binding
    src_td = create_usertd(vm_factory, "src", migtds[0], mig_hash=MIG_HASH)
    
    # create dest userTD binding with migTD directly
    dst_td = create_usertd(vm_factory, "dst", migtds[1], src_td=src_td)

    # pre-migration
    kill_socat_connect()
    socat_runner = create_socat_connect(vsock="1245")
    time.sleep(6)

    # src userTD will bind with migtd before pre-migration
    src_td.vmm.pre_migration(value=1245, pre_binding=True)
    dst_td.vmm.pre_migration(value=1246)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # start td-migration
    src_td.vmm.migrate(port="6666")

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

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = src_td.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # clean up
    for td in migtds:
        td.destroy()
    src_td.destroy()
    dst_td.destroy()

    socat_runner.terminate()

def test_td_migration_dst_pre_binding(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Destonation user TD uses pre-binding

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source userTD using pre-binding
    src_td = create_usertd(vm_factory, "src", migtds[0])
    
    # create dest userTD binding with migTD directly
    dst_td = create_usertd(vm_factory, "dst", migtds[1], src_td=src_td,mig_hash=MIG_HASH)

    # pre-migration
    kill_socat_connect()
    socat_runner = create_socat_connect()
    time.sleep(6)
    # src userTD will bind with migtd before pre-migration
    src_td.vmm.pre_migration(value=1234)
    dst_td.vmm.pre_migration(value=1235, pre_binding=True)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # start td-migration
    src_td.vmm.migrate(port="6666")

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

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = src_td.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # clean up
    for td in migtds:
        td.destroy()
    src_td.destroy()
    dst_td.destroy()

    socat_runner.terminate()

def test_td_migration_both_pre_binding(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Both source userTD and destination userTD use pre-binding

    """
    # Start two migtds
    migtds = create_couple_migtds(vm_factory)

    # Start source and destination userTD. Both use pre-binding
    couple_tds = create_couple_tds(vm_factory, migtds, mig_hash=MIG_HASH)
    src_td = couple_tds[0]
    dst_td = couple_tds[1]

    # Pre-migration for tdvms. migtd will bind with user TD before pre-migration
    kill_socat_connect()
    socat_runner = create_socat_connect(tcp_port=9008, vsock=1234)
    time.sleep(6)

    src_td.vmm.pre_migration(value=1234, pre_binding=True)
    dst_td.vmm.pre_migration(value=1235, pre_binding=True)
    time.sleep(3)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # Start td-migration
    src_td.vmm.migrate(port="6666")

    # Run mysql workload on the source userTD during td-migration
    cmd = "/root/workload-test.sh -r " + MYSQL_LOOP
    runner = src_td.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"
    time.sleep(20)

    # Check whether TD migration is done
    # Check migration is done from qmp migration status
    assert src_td.vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time is %d" % src_td.vmm.wait_for_migrate_done()[1])

    # Check migration is done from dmesg message
    assert check_migration(dst_td.name), "Migration failed. No migration flow is done in dmesg."

    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = src_td.ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # Clean up
    for td in migtds+couple_tds:
        td.destroy()

    socat_runner.terminate()

def test_td_migration_mix_pre_binding(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    2 pairs of TDs migration. 1 uses pre-binding while another does not

    """
    # Start two migtds
    migtds = create_couple_migtds(vm_factory)

    # Create 2 pairs of userTDs. One using pre-binding and another not
    couple_td0 = create_couple_tds(vm_factory, migtds, mig_hash=MIG_HASH)
    couple_td1 = create_couple_tds(vm_factory, migtds, incoming_port="5555")
    src_tds = [couple_td0[0], couple_td1[0]]
    dst_tds = [couple_td0[1], couple_td1[1]]

    # Pre-migration for both pairs of userTDs
    kill_socat_connect()
    socat_runner1 = create_socat_connect(tcp_port=9008, vsock=1234)
    socat_runner2 = create_socat_connect(tcp_port=9009, vsock=1236)
    time.sleep(6)

    # The first pair of userTDs need to bing migTD before pre-migration
    src_tds[0].vmm.pre_migration(value=1234, pre_binding=True)
    dst_tds[0].vmm.pre_migration(value=1235, pre_binding=True)

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration for srcTD1 failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration for dstTD1 failed. No pre-migration is done in dmesg."

    # The second pair of userTDs pre-migration
    src_tds[1].vmm.pre_migration(value=1236)
    dst_tds[1].vmm.pre_migration(value=1237)
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

def test_td_migration_mismatch_hash(vm_factory, vm_ssh_key, vm_ssh_pubkey):
    """
    Pre-binding migtd using wrong hash.

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source userTD using pre-binding
    src_td = create_usertd(vm_factory, "src", migtds[0])
    
    # generate a ramdom hash
    mismatch_hash = hashlib.sha384(b"random migtd hash").hexdigest()

    # create dest userTD binding with migTD directly
    dst_td = create_usertd(vm_factory, "dst", migtds[1], src_td=src_td, mig_hash=mismatch_hash)

    # pre-migration
    kill_socat_connect()
    socat_runner = create_socat_connect()
    time.sleep(6)
    src_td.vmm.pre_migration(value=1234, pre_binding=True)

    # clean up
    for td in migtds:
        td.destroy()
    src_td.destroy()
    dst_td.destroy()

    socat_runner.terminate()
