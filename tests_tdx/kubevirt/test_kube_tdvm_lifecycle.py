"""
Test the stability of TDVM in kubevirt
...
"""
import datetime
import logging
import pytest
import time

__author__ = "cpio"

LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


@pytest.mark.repeat(100)
@pytest.mark.kubevirt
def test_tdvm_lifecycle(kubevirt_tdvm):
    """
    Test if can get td-report in TD guest
    """
    # start tdvm in kubevirt
    kubevirt_tdvm.create()
    kubevirt_tdvm.start()
    kubevirt_tdvm.wait_for_ssh_ready()

    kubevirt_tdvm.shutdown()
    kubevirt_tdvm.destroy()

