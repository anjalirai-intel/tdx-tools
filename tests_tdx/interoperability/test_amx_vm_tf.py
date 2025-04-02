"""
This test module provides the basic tensorflow workload testing for TDXMA (TDX with AMX)
This test case is designed reference to :
    https://www.intel.com/content/www/us/en/developer/articles/guide/optimization-for-tensorflow-installation-guide.html
"""
import re
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_TD, VM_TYPE_EFI, VM_TYPE_LEGACY, VMSpec


__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_name("td-amx-vm"),
    pytest.mark.vm_kernel("latest-guest-kernel"),
    pytest.mark.vm_image("latest-ai-image"),
]


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD, VM_TYPE_EFI, VM_TYPE_LEGACY])
def test_vm_tf_infer_mobilenetv1_bf16(vm_factory, vm_type, vm_ssh_pubkey, vm_ssh_key):
    """
    Test MobileNetV1 inference with BF18:
    Ref: https://github.com/IntelAI/models/blob/master/benchmarks/ \
    image_recognition/tensorflow/mobilenet_v1/README.md#bfloat16-inference-instructions
    """
    LOG.info("Create TD guest to test tensorflow")
    td_inst = vm_factory.new_vm(vm_type, vmspec=VMSpec.model_large())

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    td_inst.wait_for_ssh_ready()

    command = '''
    cd /root/models-2.5.0 && DNNL_MAX_CPU_ISA=AVX512_CORE_AMX OMP_NUM_THREADS=16
    KMP_AFFINITY=granularity=fine,verbose,compact python3 ./benchmarks/launch_benchmark.py
    --benchmark-only --framework tensorflow --model-name mobilenet_v1
    --mode inference --precision bfloat16 --batch-size 1
    --in-graph /root/mobilenet_v1_1.0_224_frozen.pb
    --num-intra-threads 16 --num-inter-threads 1 --verbose --
    input_height=224 input_width=224 warmup_steps=20 steps=20
    input_layer='input' output_layer='MobilenetV1/Predictions/Reshape_1'
     '''

    runner = td_inst.ssh_run(command.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # throughput should not be 0
    patt_ok = r'Average Throughput: (\d*.\d*) images/s on 20 iterations'
    match = re.search(patt_ok, '\n'.join(runner.stdout))
    assert match is not None
    images_per_s = match.group(1)
    LOG.info(f'Throughput: {images_per_s} images/s')
    assert float(images_per_s) > 0


@pytest.mark.parametrize("vm_type", [VM_TYPE_TD, VM_TYPE_EFI, VM_TYPE_LEGACY])
def test_vm_tf_infer_dien_bf16(vm_factory, vm_type, vm_ssh_pubkey, vm_ssh_key):
    """
    Test DIEN inference with BF18:
    Ref: https://github.com/IntelAI/models/tree/master/benchmarks/ \
    recommendation/tensorflow/dien#bfloat16-inference
    """
    LOG.info("Create TD guest to test tensorflow")
    td_inst = vm_factory.new_vm(vm_type, vmspec=VMSpec.model_large())

    # customize the VM image
    td_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    td_inst.create()
    td_inst.start()
    td_inst.wait_for_ssh_ready()

    command = '''
    cd /root/models-2.5.0 && DNNL_MAX_CPU_ISA=AVX512_CORE_AMX OMP_NUM_THREADS=16
    KMP_AFFINITY=granularity=fine,verbose,compact python3 ./benchmarks/launch_benchmark.py
    --model-name dien  --mode inference  --precision bfloat16
    --framework tensorflow --data-location /root/dien
    --exact-max-length=100 --num-inter-threads 1  --num-intra-threads 16
    --batch-size 8 --graph-type=static
    --in-graph /root/dien_fp32_static_rnn_graph.pb
    --benchmark-only --verbose --
     '''
    runner = td_inst.ssh_run(command.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    # throughput should not be 0
    patt_ok = r'Approximate accelerator performance in recommendations/second is (\d*.\d*)'
    match = re.search(patt_ok, '\n'.join(runner.stdout))
    assert match is not None
    images_per_s = match.group(1)
    LOG.info(f'Throughput: {images_per_s} recommendations/s')
    assert float(images_per_s) > 0
