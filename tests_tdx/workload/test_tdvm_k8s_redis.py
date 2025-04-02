"""
This test module provides the redis workload testing for TDVM on Kubernetes
This benchmark test case is designed reference to :
         https://redis.io/topics/benchmarks
"""
import os
import logging
import pytest
import yaml
from string import Template
from pycloudstack.cluster import ClusterBase

__author__ = 'cpio'

LOG = logging.getLogger(__name__)
CURR_DIR = os.path.dirname(__file__)
NAMESPACE = 'test-tdvm-k8s'
TIMEOUT = 300
INTERVAL = 20


@pytest.fixture(scope="module")
def k8s_instance():
    """
    This fixture create a cluster instance and initialize the templates of
    deployment, service and job
    """
    k8s_config_file = os.path.join(CURR_DIR, "k8s-config.yaml")
    cluster = ClusterBase(k8s_config_file)

    # check whether td-guest node is ready
    node_status = cluster.get_node_ready_status("td-guest")
    assert "True" in node_status, "Node td-guest is not ready! Please refer to README.md"

    assert cluster.create_namespace(NAMESPACE)
    cluster.interval = INTERVAL
    cluster.timeout = TIMEOUT
    with open(k8s_config_file) as fobj:
        tpl_section = yaml.safe_load(fobj)['templates']
        deploy_tpl = Template(tpl_section['deployment'])
        svc_tpl = Template(tpl_section['service'])
        job_tpl = Template(tpl_section['job'])
        yield cluster, deploy_tpl, svc_tpl, job_tpl

    assert cluster.delete_namespace(NAMESPACE)


@pytest.mark.regression
def test_tdvm_k8s_redis(k8s_instance):
    """
    Run redis benchmark test from a job of Kubernetes
    Ref: https://redis.io/topics/benchmarks

    Use official container_image redis:latest
    Test Steps:
    1. Create cluster instance and templates from fixture
    2. Create deployment and service by templates with redis parameters
    3. Create a redis-benchmark job to test the redis service
    4. Verify the test result by redis-benchmark output '100000 requests completed'
    5. Clean environment, delete job, service and deployment
    """
    cluster, deploy_tpl, svc_tpl, job_tpl = k8s_instance

    # configure deployment and service from templates
    redis_deploy_tpl = deploy_tpl.substitute(name='tdx-redis-deployment', app='tdx-redis', port=6379,
                                             container_name='redis', container_image='redis:latest')
    redis_deploy = yaml.safe_load(redis_deploy_tpl)
    redis_svc_tpl = svc_tpl.substitute(name='tdx-redis-service', app='tdx-redis', port=6379)
    redis_svc = yaml.safe_load(redis_svc_tpl)

    # create deployment and service
    ret = cluster.create_deployment('tdx-redis-deployment', redis_deploy, NAMESPACE)
    assert ret, 'Create redis deployment failed'
    ret = cluster.create_service('tdx-redis-service', redis_svc, NAMESPACE)
    assert ret, 'Create redis service failed'
    svc_ip, svc_port = cluster.get_service_port('tdx-redis-service', NAMESPACE)
    LOG.info('service tdx-redis-service: %s:%d', svc_ip, svc_port)

    # test redis by redis-benchmark in a job
    redis_bench_tpl = job_tpl.substitute(name='tdx-redis-bench', container_name='redis',
                                         container_image='redis:latest', cmd=['redis-benchmark'],
                                         args=['-h', svc_ip, '-p', str(svc_port)])
    redis_bench_job = yaml.safe_load(redis_bench_tpl)
    ret = cluster.create_job('tdx-redis-bench', redis_bench_job, NAMESPACE)
    assert ret, 'Create redis-bench job failed'
    # verify the pod output
    pods = cluster.get_pods_by_selector('job-name=tdx-redis-bench', NAMESPACE)
    pod_name = pods.items[0].metadata.name
    logs = cluster.get_pod_log(pod_name, NAMESPACE)
    assert '100000 requests completed' in logs

    # clean, delete job and service and deployment
    ret = cluster.delete_job('tdx-redis-bench', NAMESPACE)
    assert ret, "Job tdx-redis-bench delete failed"
    ret = cluster.delete_service('tdx-redis-service', NAMESPACE)
    assert ret, "Service tdx-redis-service delete failed"
    ret = cluster.delete_deployment('tdx-redis-deployment', NAMESPACE)
    assert ret, "Deployment tdx-redis-deployment delete failed"
