"""
Test live migration performance.

"""
import logging
import os
import pytest

from pycloudstack.cmdrunner import NativeCmdRunner

__author__ = 'cpio'

LOG = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)



# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),
    pytest.mark.vm_image("latest-pts-image"),
]



def test_single_host(vm_image):
    """
    Live migration on single host
    """
    cmp_test = os.path.join(CURR_DIR, "migration_cmp_test.sh")
    cwd = os.getcwd()
    test_runner = NativeCmdRunner(cmdarr=[cmp_test, "-i", "1", "-f", vm_image, "-w", cwd])
    test_runner.runwait()
    if test_runner.retcode != 0:
        LOG.warning("test_runner.retcode %d", test_runner.retcode)
