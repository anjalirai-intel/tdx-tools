"""
This test module provides the basic tensorflow workload testing for TDVM
This test case is designed reference to :
    https://software.intel.com/content/www/us/en/develop/articles/containers/mobilenetv1-fp32-inference-tensorflow-container.html
"""
import os
import datetime
import logging
import pytest

__author__ = "cpio"

LOG = logging.getLogger(__name__)

DATE_SUFFIX = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


@pytest.mark.kubevirt
def test_amber_get_quote(vm_ssh_key, kubevirt_tdvm):
    """
    Test if amber-cli can get quote in TD guest
    """

    # start tdvm in kubevirt
    kubevirt_tdvm.create()
    kubevirt_tdvm.start()
    kubevirt_tdvm.wait_for_ssh_ready()

    command = '''
        docker run
        --env DATASET_DIR=/root/tf/data
        --env OUTPUT_DIR=/root/tf/log
        --env http_proxy=%s
        --env https_proxy=%s
        --volume /root/tf/data:/root/tf/data
        --volume /root/tf/log:/root/tf/log
        --privileged --init -t --rm
        intel/image-recognition:tf-latest-mobilenet-v1-fp32-inference
        /bin/bash quickstart/fp32_batch_inference.sh
        ''' % (os.getenv('http_proxy'), os.getenv('https_proxy'))

    ssh_runner = kubevirt_tdvm.ssh_run(command.split(), vm_ssh_key)

    kubevirt_tdvm.shutdown()
    kubevirt_tdvm.destroy()

    assert ssh_runner.retcode == 0, "Failed to execute ssh command"
    LOG.info(ssh_runner.stdout[0])
