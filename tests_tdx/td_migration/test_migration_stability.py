"""
Do single host td-migration stability test
"""
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


@pytest.mark.repeat(200)
def test_td_migration(vm_factory, vm_ssh_key):
    """
    Stability test for td-migration

    """
    # start two migtds
    migtds = create_couple_migtds(vm_factory)

    # create source and dest TDVM
    couple_tds = create_couple_tds(vm_factory, migtds, incoming_port="6666")

    # pre-migration
    kill_socat_connect()
    socat_runner = create_socat_connect()
    time.sleep(5)
    couple_tds[0].vmm.pre_migration(1234)
    couple_tds[1].vmm.pre_migration(1235)
    time.sleep(5) # wait for pre-migration ready

    # Check whether pre-migration is done
    assert check_pre_mig(migtds[0].pid), "Pre-migration failed. No pre-migration is done in dmesg."
    assert check_pre_mig(migtds[1].pid), "Pre-migration failed. No pre-migration is done in dmesg."

    # start td-migration
    couple_tds[0].vmm.migrate(port="6666")

    # run mysql workload during td-migration
    cmd = "/root/workload-test.sh -r " + MYSQL_LOOP
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key, no_wait=True)

    # Check whether TD migration is done
    # Check migration is done from qmp migration status
    assert couple_tds[0].vmm.wait_for_migrate_done()[0], "Migration failed. Cannot see migration completed in qemu monitor after 300s."

    # Display total time of migration
    LOG.info("Total migration time is %d" % couple_tds[0].vmm.wait_for_migrate_done()[1])

    # Check whether workloads keep running
    # 1. nginx
    time.sleep(60)
    cmd = f"wget -qO- --no-proxy --timeout=5 --tries=2 http://{couple_tds[0].get_ip()}:80"
    native_runner = NativeCmdRunner(cmd.split())
    native_runner.runwait()
    assert "Welcome to nginx!" in native_runner.stdout[13], "nginx hangs"

    # 2. mysql
    # Check whether mysql keeps running specific cycles meaning mysql is not interrupted during migration
    # Also check the status of ssh
    cmd = 'cat /tmp/mysqldir/result.txt'
    runner = couple_tds[0].ssh_run(cmd.split(), vm_ssh_key)
    assert runner.stdout[0] == MYSQL_LOOP, "mysql does not keeps running"

    # clean up
    for td in migtds+couple_tds:
        td.destroy()

    socat_runner.terminate()
