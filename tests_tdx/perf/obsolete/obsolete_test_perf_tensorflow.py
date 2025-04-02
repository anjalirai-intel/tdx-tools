"""
Do performance measuring and comparition for tensorflow between legacy VM and TDVM.
"""
import os
import logging
import time
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_LEGACY

__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_kernel("latest-guest-kernel"),       # from artifacts.yaml
    pytest.mark.vm_image("latest-guest-test-image"),    # from artifacts.yaml
]


@pytest.mark.skip(reason="The output log is too large")
def test_tdvm_tensorflow_simple(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    Collect tensorflow-bench performance for TD guest

    1. Run 3 round benchmark
    2. Save the result will be put into output/tensorflow-perf-tdvm directory

    """
    LOG.info("Create TD guest to run tensorflow benchmark")
    td_inst = vm_factory.new_vm(VM_TYPE_TD)

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    assert td_inst.wait_for_ssh_ready(), "Boot timeout"

    os.makedirs(os.path.join(output, "tensorflow-perf-tdvm"), exist_ok=True)

    for index in range(3):
        command_list = [
            'systemctl start docker',
            'docker ps',
            f'''
            docker run \
            --env DATASET_DIR=/root/tf/data \
            --env OUTPUT_DIR=/root/tf/log \
            --env http_proxy={os.getenv('http_proxy')} \
            --env https_proxy={os.getenv('https_proxy')} \
            --volume /root/tf/data:/root/tf/data \
            --volume /root/tf/log:/root/tf/log \
            --privileged --init -t \
            intel/image-recognition:tf-2.4.0-mobilenet-v1-fp32-inference \
            /bin/bash quickstart/fp32_batch_inference.sh'''
        ]

        stdout = ""
        for cmd in command_list:
            runner = td_inst.ssh_run(cmd.split(), vm_ssh_key)
            assert runner.retcode == 0, "Failed to execute remote command"

        timestr = time.strftime("%Y_%m_%d-%H_%M_%S")
        outfile_path = os.path.join(
            output, "tensorflow-perf-tdvm", f"{timestr}-{index}.txt")
        with open(outfile_path, "w+", encoding="utf8") as fobj:
            fobj.write(stdout)


@pytest.mark.skip(reason="The output log is too large")
def test_legacy_tensorflow_simple(vm_factory, vm_ssh_pubkey, vm_ssh_key, output):
    """
    Collect tensorflow-bench performance for legacy guest

    1. Run 3 rounds tensorflow bench
    2. Save the result will be put into output/tensorflow-perf-legacy directory

    """

    LOG.info("Create TD guest to run tensorflow benchmark")
    vm_inst = vm_factory.new_vm(VM_TYPE_LEGACY)

    # customize the VM image
    vm_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    vm_inst.create()
    vm_inst.start()
    assert vm_inst.wait_for_ssh_ready(), "Boot timeout"

    os.makedirs(os.path.join(output, "tensorflow-perf-legacy"), exist_ok=True)

    for index in range(3):
        command_list = [
            'systemctl start docker',
            'docker ps',
            f'''
            docker run
            --env DATASET_DIR=/root/tf/data
            --env OUTPUT_DIR=/root/tf/log
            --env http_proxy={os.getenv('http_proxy')}
            --env https_proxy={os.getenv('https_proxy')}
            --volume /root/tf/data:/root/tf/data
            --volume /root/tf/log:/root/tf/log
            --privileged --init -t
            intel/image-recognition:tf-2.4.0-mobilenet-v1-fp32-inference
            /bin/bash quickstart/fp32_batch_inference.sh
            '''
        ]

        stdout = ""
        for cmd in command_list:
            LOG.debug(cmd)
            runner = vm_inst.ssh_run(cmd.split(), vm_ssh_key)
            assert runner.retcode == 0, "Failed to execute remote command"

        timestr = time.strftime("%Y_%m_%d-%H_%M_%S")
        outfile_path = os.path.join(
            output, "tensorflow-perf-legacy", f"{timestr}-{index}.txt")
        with open(outfile_path, "w+", encoding="utf8") as fobj:
            fobj.write(stdout)
