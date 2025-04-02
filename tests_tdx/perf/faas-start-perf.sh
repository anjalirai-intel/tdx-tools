#!/bin/bash

set +e  # not quit for failure command

# By default, use the same directory as this script as output directory
OUTPUT_DIR=$(dirname "$(readlink -f "$0")")
# Default openfaas function test loops
LOOP=100
# Time to wait for the cluster or openfaas deployment to be ready
RETRY=120

usage() {
    cat << EOM
Usage: $(basename "$0") [OPTION]...
  -o Output directory for results
  -r <number>  round number
  -h Show this
EOM
    exit 0
}

process_args() {
    while getopts ":o:r:h" option; do
        case "${option}" in
            o) OUTPUT_DIR=$(readlink -f ${OPTARG});;
            r) LOOP=${OPTARG};;
            h) usage;;
        esac
    done

    if [[ ! -d $OUTPUT_DIR ]]; then
        mkdir -p $OUTPUT_DIR
    fi
}

faas_setup() {
    # Create a Kubernetes cluster with one control plane and two worker nodes:
    /root/go/bin/kind create cluster --config ./openfaas-cluster.yaml
    if [ $? != 0 ]; then
        echo "Failed to create the K8S cluster!"
	exit 1
    fi

    # Install arkade following https://github.com/alexellis/arkade#getting-arkade
    curl -sLS https://get.arkade.dev | sudo sh

    # Insall 'openfaas'
    arkade install openfaas
    if [ $? != 0 ]; then
        echo "Failed to install OpenFaas!"
	exit 1
    fi

    # Load 'openfaas' component images
    docker pull prom/alertmanager:v0.25.0
    docker pull nats-streaming:0.25.5
    docker pull prom/prometheus:v2.45.0
    /root/go/bin/kind load docker-image prom/alertmanager:v0.25.0 nats-streaming:0.25.5 prom/prometheus:v2.45.0

    # Wait for the openfaas pods to get ready
    # 30 is an empirical value, otherwise will wait for
    # extra $RETRY seconds
    sleep 30

    i=0;
    while [ $i -lt $RETRY ]
    do
	if kubectl get deployments -n openfaas | grep -q "0/1"
	then
            sleep 1
	    i=$[$i+1]
	else
	    break
	fi
    done
    if [ $i -ge $RETRY ]; then
	echo "Fail to initializate the OpenFaas App!"
	exit 1
    fi

    # Forward all requests made to http://localhost:8080 to the pod
    # running the gateway service
    kubectl port-forward -n openfaas svc/gateway 8080:8080 &

    sleep 1

    # Since the function image was pushed to docker hub and there
    # are image download limits there, need to login the docker hub
    # when deploying function in the cluster.
    docker login

    # Login to local instance of the OpenFaaS gateway
    PASSWORD=$(kubectl get secret -n openfaas basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode; echo)
    echo -n $PASSWORD | faas-cli login --username admin --password-stdin
    if [ $? != 0 ]; then
        echo "Failed to login to the local OpenFaas gateway!"
	exit 1
    fi

    # Deploy the serverless function
    faas-cli deploy -f bash-fn.yml
    if [ $? != 0 ]; then
        echo "Failed to deploy the serverless function!"
	exit 1
    fi

    # Get the function status and wait for it get ready!
    i=0;
    while [ $i -lt $RETRY ]
    do
	if faas-cli describe bash-fn | grep -q "Ready"; then
	    break
	fi
        sleep 1
	i=$[$i+1]
    done
    if [ $i -ge $RETRY ]; then
	echo "The bash function was not ready!"
	exit 1
    fi
}

faas_cleanup() {
    # Delete the Kubenetes cluster, or the SSH connect would
    # got hang for the sake of TD network re-cofiguration when
    # creating cluster!
    echo "Delete the Kubenetes Cluster!"
    /root/go/bin/kind delete cluster
}

run_benchmark() {
    now=$(date +"%Y_%m_%d-%H_%M_%S")

    # Warm up
    for i in `seq 20`
    do
	curl -s http://127.0.0.1:8080/function/bash-fn >2
    done

    # Run benchmark
    for i in `seq $LOOP`
    do
	(time curl -s http://127.0.0.1:8080/function/bash-fn) 2>> ${OUTPUT_DIR}/faas-start-perf-data-${now}.txt
	sync
    done

    # Output the average result
    awk '/real/ {print $2}' ${OUTPUT_DIR}/faas-start-perf-data-${now}.txt |
    awk -F m '{if ($1==0) print substr($2, 0, 5)}' |
    awk 'BEGIN { sum=0 } { sum+=$1 } END {print "Average faas start up time: ", sum/NR }'
}

process_args $@
faas_setup
run_benchmark
faas_cleanup
