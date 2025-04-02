# Run TDX K8S workload tests

## 1. Overview

This document describes how to setup a td-guest node and join Kubernets cluster for k8s workload tests.

## 2. Prerequisites

- Assume there is a k8s cluster running. You have kubectl command line tool installed and well configured to communite with the cluster.

- Create bridge on the host where the td-guest will be created

    Create file with name "host" to point to target host where the playbook actions will be run, the content is "username@host-ip", e.g. ruomeng@cpio-sprac-prc4.sh.intel.com

    Inject ssh key to target host to make sure ssh connection to target host will be password free.

    Run "ansible-playbook -i host bridge.yml"

- After above steps, a bridge "br0" is expected to be created

## 3. Setup td-guest node

- In tdx-k8s.xml file, replace "REPLACE_PATH" with your own path

- Create td-guest VM

    ```bash
    virsh define tdx-k8s-ubuntu-guest.xml
    virsh start td-guest
    ```

- Connect to td-guest, and the following steps will run in td-guest VM

- Install kubeadm in td-guest

    ```bash
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl
    curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
    echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
    apt-get update
    apt-get install -y kubelet kubeadm kubectl
    apt-mark hold kubelet kubeadm kubectl
    ```

- Add proxy to containerd conf

    ```bash
    mkdir /etc/systemd/system/containerd.service.d/
    cat <<EOF> /etc/systemd/system/containerd.service.d/http-proxy.conf
    [Service]
    Environment=HTTP_PROXY=http://child-prc.intel.com:913
    Environment=HTTPS_PROXY=http://child-prc.intel.com:913
    Environment=NO_PROXY=localhost,127.0.0.1
    EOF

- Change hostname to td-guest

    ```bash
    hostnamectl --static set-hostname td-guest
    ```

## 4. td-guest join to k8s cluster

- Get join cluster command from client which can communicate with k8s cluster

    ```bash
    kubeadm token create --print-join-command
    ```

- Run the output of above command in td-guest

- Check whether td-guest join cluster successfully. When td-guest is listed as "Ready",
it's successful.

    ```bash
    kubectl get node -o wide
    ```

- If the node stays in "NotReady", describe the pods on td-guest and find out the reason.

    ```bash
    kubectl get pods --all-namespaces
    kubectl describe pod <pod-name> -n kube-system
    ```

- Please replace the corresponding paramters in k8s-config.yaml with your own "~/.kube/config" content if you are using your own cluster.
