'''
This test module provides the basic tensorflow workload testing for AMX in SGX
This test case is designed reference to :
    https://github.com/IntelAI/models/tree/v2.5.0/benchmarks
'''
import re
import logging
import pytest
from pycloudstack.vmparam import VM_TYPE_SGX, VM_TYPE_EFI, VMSpec, SGXVMSpec


__author__ = 'cpio'

LOG = logging.getLogger(__name__)

# pylint: disable=invalid-name
pytestmark = [
    pytest.mark.vm_name('td-amx-sgx'),
    pytest.mark.vm_kernel('latest-guest-kernel'),
    pytest.mark.vm_image('latest-ai-image'),
]


def validate_output(output):
    # throughput should not be 0
    patt_ok = r'Throughput: (\d*.\d*) images/sec'
    match = re.search(patt_ok, '\n'.join(output))
    assert match is not None
    images_per_s = match.group(1)
    LOG.info(f'Throughput: {images_per_s} images/sec')
    assert float(images_per_s) > 0


@pytest.mark.parametrize('model_type', ['int8', 'bf16', 'fp32'])
def test_vm_amx_sgx_tf_infer_resnet50(vm_factory, model_type, vm_ssh_pubkey, vm_ssh_key):
    '''
    Test ResNet50 V1.5 inference with INT8/BF16/FP32:
    Ref: https://github.com/IntelAI/models/tree/v2.5.0/benchmarks/image_recognition/tensorflow/resnet50v1_5
    '''
    LOG.info('Create TD guest to test tensorflow')

    models = {'int8': 'resnet50v1_5_int8_pretrained_model.pb',
              'bf16': 'resnet50_v1_5_bfloat16.pb',
              'fp32': 'resnet50_v1_5_bfloat16.pb'}

    epc = [{'size': '16G', 'prealloc': True, 'node': 0}]
    AISpec = SGXVMSpec(sockets=1, cores=8, threads=1, memsize=(64 * 1024 * 1024), epc=epc)
    sgx_inst = vm_factory.new_vm(VM_TYPE_SGX, vmspec=AISpec)

    # customize the VM image
    sgx_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    sgx_inst.create()
    sgx_inst.start()
    sgx_inst.wait_for_ssh_ready()

    command = f'''
    docker run --rm --device=/dev/sgx_enclave -e DNNL_MAX_CPU_ISA=AVX512_CORE_AMX
    -e OMP_NUM_THREADS=8 -e KMP_AFFINITY=granularity=fine,verbose,compact
    gsc-ubuntu20.04-tensorflow -c "gramine-sgx /entrypoint
    /models-2.5.0/models/image_recognition/tensorflow/resnet50v1_5/inference/eval_image_classifier_inference.py
    --input-graph=/pre-trained-models/{models[model_type]}
    --num-inter-threads=1 --num-intra-threads=8 --batch-size=8 --warmup-steps=50 --steps=500"
     '''
    runner = sgx_inst.ssh_run(command.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"

    validate_output(runner.stdout)
    sgx_inst.destroy(delete_image=True, delete_log=True)


def test_vm_amx_sgx_coexist(vm_factory, vm_ssh_pubkey, vm_ssh_key):
    '''
    Test legacy guest and SGX guest coexistance, and both runing AMX workloads
    '''
    epc = [{'size': '16G', 'prealloc': True, 'node': 0}]
    AISpec = SGXVMSpec(sockets=1, cores=8, threads=1, memsize=(64 * 1024 * 1024), epc=epc)
    sgx_inst = vm_factory.new_vm(VM_TYPE_SGX, vmspec=AISpec)
    # customize the VM image
    sgx_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    sgx_inst.create()
    sgx_inst.start()
    sgx_inst.wait_for_ssh_ready()

    amx_inst = vm_factory.new_vm(VM_TYPE_EFI, vmspec=VMSpec.model_large())
    # customize the VM image
    amx_inst.image.inject_root_ssh_key(vm_ssh_pubkey)

    # create and start VM instance
    amx_inst.create()
    amx_inst.start()
    amx_inst.wait_for_ssh_ready()

    sgx_command = '''
    docker run --rm --device=/dev/sgx_enclave -e DNNL_MAX_CPU_ISA=AVX512_CORE_AMX
    -e OMP_NUM_THREADS=8 -e KMP_AFFINITY=granularity=fine,verbose,compact
    gsc-ubuntu20.04-tensorflow -c "gramine-sgx /entrypoint
    /models-2.5.0/models/image_recognition/tensorflow/resnet50v1_5/inference/eval_image_classifier_inference.py
    --input-graph=/pre-trained-models/resnet50v1_5_int8_pretrained_model.pb
    --num-inter-threads=1 --num-intra-threads=8 --batch-size=8 --warmup-steps=50 --steps=500"
     '''
    runner = sgx_inst.ssh_run(sgx_command.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"
    validate_output(runner.stdout)

    amx_command = '''
    docker run --rm -e DNNL_MAX_CPU_ISA=AVX512_CORE_AMX
    -e OMP_NUM_THREADS=8 -e KMP_AFFINITY=granularity=fine,verbose,compact
    gsc-ubuntu20.04-tensorflow -c "python3
    /models-2.5.0/models/image_recognition/tensorflow/resnet50v1_5/inference/eval_image_classifier_inference.py
    --input-graph=/pre-trained-models/resnet50v1_5_int8_pretrained_model.pb
    --num-inter-threads=1 --num-intra-threads=8 --batch-size=8 --warmup-steps=50 --steps=500"
     '''
    runner = amx_inst.ssh_run(amx_command.split(), vm_ssh_key)
    assert runner.retcode == 0, "Failed to execute remote command"
    validate_output(runner.stdout)

    sgx_inst.destroy(delete_image=True, delete_log=True)
    amx_inst.destroy(delete_image=True, delete_log=True)
