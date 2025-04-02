#!/bin/bash

set +e  # not quit for failure command
set -x

# By default, use the same directory as this script as output directory
OUTPUT_DIR=$(dirname "$(readlink -f "$0")")
WARMUP_NUM=0
ROUND_NUM=1

usage() {
    cat << EOM
Usage: $(basename "$0") [OPTION]...
  -o Output directory for results
  -w <number>  warmup number
  -r <number>  round number
  -h Show this
EOM
    exit 0
}

process_args() {
    while getopts ":o:w:r:h" option; do
        case "${option}" in
            o) OUTPUT_DIR=$(readlink -f ${OPTARG});;
            w) WARMUP_NUM=${OPTARG};;
            r) ROUND_NUM=${OPTARG};;
            h) usage;;
        esac
    done

    if [[ ! -d $OUTPUT_DIR ]]; then
        mkdir -p $OUTPUT_DIR
    fi
}

cleanup() {
    # Stop existing nginx server container if need (optional)
    docker stop tdx-nginx || true
    while docker container inspect tdx-nginx >/dev/null 2>&1; do sleep 1; done
}

start_nginx_server() {
    # Start nginx-server
    docker run --rm -d --name tdx-nginx nginx
    while true
    do
        if docker ps -a --format '{{.Names}}' | grep -Eq "^tdx-nginx\$"; then
            break
        fi
    sleep 1
    done

    # Get the container IP
    NGINX_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' tdx-nginx)
    echo "Nginx service is started at $NGINX_IP"

    # Wait for nginx completed work and ready
    count=0
    while true
    do
        </dev/tcp/$NGINX_IP/80
        if [[ $? == 0 ]]; then
            echo "Success start nginx-server in docker."
            break
        else
            ((count++))
            if (( $count > 10 )); then
                echo "Fail to run nginx service after 10 seconds. ret: $ret"
                exit 1
            fi
            echo "nginx server is not ready yet, wait for more seconds..."
            sleep 1
        fi
    done
}

run_benchmark() {
    # Warm up
    if (( $WARMUP_NUM > 0 )); then
        echo "Warm up ..."
        for i in `seq $WARMUP_NUM`; do
            echo "  Warmup - $i times"
            siege -t 1M -b http://$NGINX_IP:80
        done
    fi

    # Measure
    now=$(date +"%Y_%m_%d-%H_%M_%S")
    for i in `seq $ROUND_NUM`; do
        echo "$i round performance for nginx!"
        # Run benchmark
        siege -t 1M -b http://$NGINX_IP:80 > ${OUTPUT_DIR}/nginx-perf-data-${now}-${i}.txt
        ret=$?
        if [[ $ret -eq 0 ]];
        then
            echo "Success to run nginx service in docker and siege"
            sync
            sleep 2
        else
            echo "Fail to run siege, ret: $ret"
            exit $ret
        fi
    done

    # Output
    cat ${OUTPUT_DIR}/*.txt
    echo "Complete the benchmark.."
}

process_args $@
cleanup
start_nginx_server
run_benchmark