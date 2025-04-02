![PR Checking](https://github.com/intel-innersource/os.linux.cloud.tdx.stack-test/actions/workflows/pr-check.yml/badge.svg)

# Linux TDX MVP Stack Test Suite

## 1. Overview

The TDX MVP Stack test suite is running on the TDX host including platform configurations, TDVM's lifecycle,
TDVM environment, typical workload and performance testings. It bases on the [pytest](https://docs.pytest.org/en/6.2.x/)
framework.

## 2. Licenses

Almost all test cases are under [Apache2 license](LICENSE), except the test cases under tests_tdx/gpl are GPL2.0.

## 3. Dependencies & Requirements

- TDX MVP stacks already been deployed on the TDX host.

- Install DNF packages

    ```
    sudo dnf install python3-virtualenv python3-libvirt-6.0.0 libguestfs-devel libvirt-devel python3-devel iperf3
    ```

- Setup environment

    Run below command to setup the python environment

    ```
    source setupenv.sh
    ```
    _NOTE:_
    - All dependent packages will be installed into `<this_repo_dir>/venv`
    - If fail to download the python PIP packages from offical PIP server, please try from a mirror server,
    for example using PRC tsinghua university, create a new file ~/.pip/pip.conf with following contents:

        ```
        [global]
        timeout = 60
        index-url = https://pypi.tuna.tsinghua.edu.cn/simple
        ```


- Install pycloudstack

    _NOTE: pycloudstack already included in public release, so no need addtional installation._

    - Clone git submodule source at `<this_repo_dir>/pycloudstack`

        ```
        git submodule update --init
        ```


- Prepare guest image and guest kernel for tests

  **_NOTE_:**:  Please make sure guest image and guest kernel are from the same release or tests will fail.

  - Get guest image and guest kernel from TDX MVP Stack release artifactory. Please find release artifactory in [Release History](https://wiki.ith.intel.com/pages/viewpage.action?pageId=2292290370#Release-History)

  - Or you can create guest image via `TDX cloud image tool` for [RHEL 8](https://github.com/intel/tdx-tools/tree/main/build/rhel-8/guest-image)
or [Ubuntu 22.04](https://github.com/intel/tdx-tools/tree/main/build/ubuntu-22.04/guest-image).

- Please inject the [SSH test key](tests_tdx/vm_ssh_test_key.pub) into TDX guest image

    ```
    virt-customize -a <your-guest-image-name>.qcow2 --ssh-inject root:file:tests_tdx/vm_ssh_test_key.pub

    ```

- Create your own artifacts.yaml from [template](artifacts.yaml.template). Input your guest image and guest kernel path in artifacts.yaml. The source URI or sha256sum's URI could be remote file with the prefix of
"http://" or "https://" or local file with the prefix of "file:///"

    ```
    <artifacts name>
        source: <Source URI>
        sha256sum: <SHA256 String or the file URI contains SHA256 String>
    ```


    | Image Artifact | Description | Purpose |
    | -------------- | ----------- | ------- |
    | latest-guest-image | TDX Guest Cloud Image | Required for all testings |
    | latest-guest-kernel | TDX Guest Kernel Image | Required for all testings |
    | latest-guest-test-image | TDX Guest Test Cloud Image | Required for workload, stability testings |
    | latest-guest-pts-image | TDX Guest Phoronix Cloud Image | Required for performance testings |


## 3. Running Test

- Run a test suite: 

    ```
    ./run.sh -s <suite_name>
    ```
    For example:
    - Run BAT test suite: 
    
    ```
    sudo ./run.sh -s bat` (**_NOTE: the platform/host testings need root privilege._**)
    ```

    - Run functional test suite:
    
    ```
    ./run.sh -s functional
    ```

- Run specific test modules: 
    
    ```
    ./run.sh -c <case_module1> -c <case_module2>
    ```

    For example:
    ```
    ./run.sh -c tests_tdx/environment/test_tdvm_network.py -c tests_tdx/lifecycle/test_coexist_nontd.py
    ```

- Run specific test cases: 

    ```
    ./run.sh -c <case_module1> -c <case_module1>::<case_name>
    ```

    For example:
    ```
    ./run.sh -c tests_tdx/environment/test_tdvm_network.py::test_tdvm_wget
    ```

- User can specify guest image OS with `-g`. Currently it supports `rhel`, and `ubuntu`. Ubuntu guest image is used by default if `-g` is not specified:

    ```
    sudo ./run.sh -g rhel -s bat
    ```