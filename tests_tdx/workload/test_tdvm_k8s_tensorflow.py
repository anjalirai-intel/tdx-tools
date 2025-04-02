"""
This test module provides the tensorflow workload testing for TDVM on Kubernetes
This benchmark test case is designed reference to: https://software.intel.com/content/www/
    us/en/develop/articles/containers/mobilenetv1-fp32-inference-tensorflow-container.html
"""
import os
import re
import logging
import pytest
import yaml
from pycloudstack.cluster import ClusterBase

__author__ = 'cpio'

LOG = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)
NAMESPACE = 'test-tdvm-k8s'
TIMEOUT = 600
INTERVAL = 30


@pytest.fixture(scope="module")
def k8s_instance():
    """
    This fixture create a cluster instance
    """
    k8s_config_file = os.path.join(CURR_DIR, "k8s-config.yaml")
    cluster = ClusterBase(k8s_config_file)

    # check whether td-guest node is ready
    node_status = cluster.get_node_ready_status("td-guest")
    assert "True" in node_status, "Node td-guest is not ready! Please refer to README.md"

    assert cluster.create_namespace(NAMESPACE)
    cluster.interval = INTERVAL
    cluster.timeout = TIMEOUT

    yield cluster

    assert cluster.delete_namespace(NAMESPACE)


def test_tdvm_k8s_tensorflow(k8s_instance):
    """
    Run a tensorflow sample application within a job
    Note: Minimum 3GB (3145728KB) memory required in k8s node to run tensorflow
        With 2GB service will run out of memory sometimes
    Ref: https://software.intel.com/content/www/us/en/develop/articles/
        containers/mobilenetv1-fp32-inference-tensorflow-container.html
    Use docker image:intel/image-recognition:tf-2.4.0-mobilenet-v1-fp32-inference

    Test Steps:
    1. Create cluster instance and namespace
    2. Create a job to run tensorflow service
    3. Check throughput in pod logs.
    4. Clean environment, delete job
    """
    cluster = k8s_instance

    # create job from yaml config
    config_file = os.path.join(CURR_DIR, "test_tdvm_k8s_tensorflow.yaml")
    with open(config_file) as f:
        job_config = yaml.safe_load(f)
    job_name = job_config['metadata']['name']
    LOG.info(f"Start creating job {job_name}")
    ret = cluster.create_job(job_name, job_config, NAMESPACE)
    assert ret, f'Failed to create job {job_name}'

    # get logs from pod
    pods = cluster.get_pods_by_selector(f'job-name={job_name}', NAMESPACE)
    pod_name = pods.items[0].metadata.name
    logs = cluster.get_pod_log(pod_name, NAMESPACE)

    # throughput should not be 0
    patt_ok = r'Average Throughput: (\d*.\d*) images/s on 50 iterations'
    match = re.search(patt_ok, logs)
    assert match is not None
    images_per_s = match.group(1)
    LOG.info(f'Throughput: {images_per_s} images/s')
    assert float(images_per_s) > 0

    # delete job
    ret = cluster.delete_job(job_name, NAMESPACE)
    assert ret, f"Failed to delete job {job_name}"
