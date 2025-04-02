"""
This test module provides the nginx workload testing for TDVM on Kubernetes
This benchmark test case is designed reference to :
         https://hub.docker.com/r/yokogawa/siege
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


def test_tdvm_k8s_nginx(k8s_instance):
    """
    Run siege test from a job of Kubernetes
    Ref: https://hub.docker.com/r/yokogawa/siege

    Use official container_image nginx:latest
    Test Steps:
    1. Create cluster instance and templates from fixture
    2. Create deployment and service by templates with nginx parameters
    3. Create a job to run siege test service
    4. Verify the test result by siege output 'Available:  100.00 %'
    5. Clean environment, delete job, service and deployment
    """
    cluster, deploy_tpl, svc_tpl, job_tpl = k8s_instance
    app = 'tdvm_k8s_nginx'
    deploy_name = 'tdx-nginx-deployment'
    service_name = 'tdx-nginx-service'
    job_name = 'tdx-nginx-bench'

    # create deployment from template
    nginx_deploy_tpl = deploy_tpl.substitute(
        name=deploy_name, app=app,
        port=80, container_name='nginx',
        container_image='nginx:latest')
    nginx_deploy = yaml.safe_load(nginx_deploy_tpl)
    ret = cluster.create_deployment(deploy_name, nginx_deploy, NAMESPACE)
    assert ret, 'Create nginx deployment failed'

    # create service from template
    nginx_svc_tpl = svc_tpl.substitute(name=service_name, app=app, port=80)
    nginx_svc = yaml.safe_load(nginx_svc_tpl)
    ret = cluster.create_service(service_name, nginx_svc, NAMESPACE)
    assert ret, 'Create nginx service failed'

    # create job from template to run siege test
    srv_ip, srv_port = cluster.get_service_port(service_name, NAMESPACE)
    srv_web = 'http://' + srv_ip + ':' + str(srv_port)
    LOG.info('%s website: %s', service_name, srv_web)
    nginx_bench_tpl = job_tpl.substitute(
        name=job_name,
        container_name='siege',
        container_image='yokogawa/siege:latest',
        cmd=['siege'], args=['-t', '1M', srv_web])
    nginx_bench_job = yaml.safe_load(nginx_bench_tpl)
    ret = cluster.create_job(job_name, nginx_bench_job, NAMESPACE)
    assert ret, 'Create nginx-bench job failed'

    # in pod log, successful transactions should meet 100.00 %.
    pods = cluster.get_pods_by_selector(f'job-name={job_name}', NAMESPACE)
    pod_name = pods.items[0].metadata.name
    logs = cluster.get_pod_log(pod_name, NAMESPACE)
    assert '100.00 %' in logs

    # clean, delete job and service and deployment
    ret = cluster.delete_job('tdx-nginx-bench', NAMESPACE)
    assert ret, "Job tdx-nginx-bench delete failed"
    ret = cluster.delete_service('tdx-nginx-service', NAMESPACE)
    assert ret, "Service tdx-nginx-service delete failed"
    ret = cluster.delete_deployment('tdx-nginx-deployment', NAMESPACE)
    assert ret, "Deployment tdx-nginx-deployment delete failed"
