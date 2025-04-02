"""
local conftest.py plugins contain directory-specific hook implementations.
Session and test running activities will invoke all hooks defined in conftest.py
files closer to the root of the filesystem.
"""
import os
import logging
import subprocess
import hashlib
# pylint: disable=no-name-in-module,import-error,redefined-outer-name
from py.xml import html
import pytest
from pycloudstack import virtxml, artifacts
from pycloudstack.vmm import VMMKubeVirt
from pycloudstack.vmguest import VMGuestFactory, VMGuest

LOG = logging.getLogger(__name__)

TDVM_JSON = os.path.join(os.path.dirname(__file__), "kubevirt/kubevirt-tdx-test.json")

@pytest.fixture(scope="module")
def vm_name(request):
    """
    Customized VM name in module scope
    """
    name_marker = request.node.get_closest_marker("vm_name")
    return name_marker.args[0] if name_marker else request.node.name


@pytest.fixture(scope="module")
def vm_image(request, artifact_factory):
    """
    Customized VM image in module scope
    """
    cache_dir = request.config.cache.makedir('downloads')
    dest_dir = request.config.cache.makedir('vm-images')

    image_marker = request.node.get_closest_marker("vm_image")
    if not image_marker:
        raise ValueError("Missing vm_image marker")

    guest = request.config.getoption("--guest")
    image = image_marker.args[0] + '-' + guest
    if not image:
        raise ValueError("Invalid VM OS Image")
    # pylint: disable=unsubscriptable-object
    artobj = artifact_factory[image]
    assert artobj is not None, f"Fail to find the {image} in artifacts.yaml"
    return artobj.get(dest_dir, cache_dir)


@pytest.fixture(scope="module")
def vm_kernel(request, artifact_factory):
    """
    Customized VM kernel in module scope
    """
    cache_dir = request.config.cache.makedir('downloads')
    dest_dir = request.config.cache.makedir('vm-kernels')

    image_marker = request.node.get_closest_marker("vm_kernel")
    if not image_marker:
        raise ValueError("Missing vm_kernel marker")

    guest = request.config.getoption("--guest")
    kernel = image_marker.args[0] + '-' + guest
    if not kernel:
        raise ValueError("Invalid VM kernel")
    # pylint: disable=unsubscriptable-object
    artobj = artifact_factory[kernel]
    assert artobj is not None, f"Fail to find the {kernel} in artifacts.yaml"
    return artobj.get(dest_dir, cache_dir)


# pylint: disable=redefined-outer-name
@pytest.fixture(scope="module")
def vm_factory(request, vm_image, vm_kernel):
    """
    New mark for the vm factory to create different VM.
    """
    factoryobj = VMGuestFactory(vm_image, vm_kernel)
    yield factoryobj
    LOG.info("Delete factory instance for cleanup")
    keep_issue_vm = request.config.getoption("--keep-vm")
    factoryobj.set_keep_issue_vm(keep_issue_vm)
    factoryobj.removeall()
    del factoryobj


@pytest.fixture(autouse=True, scope="session")
def output(request):
    """
    Get output path
    """
    outdir = os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            request.config.getini("output_dir")))
    os.makedirs(outdir, exist_ok=True)
    virtxml.VirtXml.set_output_dir(outdir)
    return outdir


@pytest.fixture(autouse=True, scope="session")
def vm_ssh_key():
    """
    SSH key for remote running command to guest VM
    """
    return os.path.join(os.path.dirname(__file__), "vm_ssh_test_key")


@pytest.fixture(autouse=True, scope="session")
def vm_ssh_pubkey():
    """
    SSH key for remote running command to guest VM
    """
    return os.path.join(os.path.dirname(__file__), "vm_ssh_test_key.pub")


def pytest_html_results_summary(prefix, *_, **__):
    """
    Hook to refine the report
    """
    prefix.extend([html.h1("Linux TDX MVP Stack")])


#@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    """
    Expect to display version of packages in below list
    ['intel-mvp-tdx-libvirt.x86_64','intel-mvp-tdx-qemu-kvm.x86_64',
    'intel-mvp-tdx-tdvf.noarch','intel-mvp-tdx-module.x86_64',
    'intel-mvp-tdx-kernel.x86_64']
    """
    expected_lst = ['intel-mvp-tdx-libvirt.x86_64', 'intel-mvp-tdx-qemu-kvm.x86_64',
                    'intel-mvp-ovmf.noarch', 'intel-mvp-tdx-module.x86_64',
                    'intel-mvp-tdx-kernel.x86_64']
    for item in subprocess.getoutput("apt list installed").split('\n'):
        ret = item.strip().split()
        if len(ret) > 1 and ret[0] in expected_lst:
            # pylint: disable=protected-access
            session.config._metadata[ret[0]] = ret[1]
    vip_files = [
        "/usr/sbin/libvirtd",
        "/usr/lib64/libvirt.so",
        "/usr/libexec/qemu-kvm",
        "/usr/share/qemu/OVMF_CODE.fd",
        "/usr/share/qemu/OVMF_VARS.fd",
        "/boot/vmlinuz-" + os.uname().release,
        "/boot/initramfs-" + os.uname().release + ".img",
    ]
    for vipfile in vip_files:
        try:
            with open(vipfile, "rb") as fobj:
                value = hashlib.sha256(fobj.read()).hexdigest()
                # pylint: disable=protected-access
                # session.config._metadata["sha256:" + vipfile] = value
        except IOError:
            LOG.warning("Fail to open file %s", vipfile)

    LOG.info("Session exis status is %s", exitstatus)


@pytest.fixture(scope="session")
def artifact_factory(request):
    """
    The artifact factory from artifacts.yaml
    """
    manifest_file = os.path.join(os.path.dirname(__file__), request.config.getini("artifacts"))
    fobj = artifacts.ArtifactManifest(manifest_file)
    assert fobj.load() is not None
    return artifacts.ArtifactFactory(fobj)

@pytest.fixture(scope="module")
def kubevirt_tdvm(request):
    """
    Kubeconfig path
    """
    kubeconfig = request.config.getoption("--kubeconfig")
    kubevirt_tdvm = VMGuest(name="kubevirt-tdx-test", vmm_class=VMMKubeVirt)
    kubevirt_tdvm.vmm.load_kubeconfig(kubeconfig)
    kubevirt_tdvm.vmm.load_tdvm_template(tdvm_template=TDVM_JSON)
    return kubevirt_tdvm

def pytest_addoption(parser):
    """
    Config the parser
    """
    parser.addoption(
        "--keep-vm", action="store_true", default=False, help="NOT destroy unhealty VMs"
    )
    parser.addoption("--guest", action="store", default="rhel")
    parser.addoption("--kubeconfig", action="store", default="~/.kube/config")
    parser.addini("output_dir", "Output directory")
    parser.addini("artifacts", "The manifest file for artifacts")
