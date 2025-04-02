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
    # Stop existing redis server container if need (optional)
    docker stop tdx-redis || true
    while docker container inspect tdx-redis >/dev/null 2>&1; do sleep 1; done
}

start_redis_server() {
    # Start redis-server
    docker run --rm -d --name tdx-redis redis
    while true
    do
    if docker ps -a --format '{{.Names}}' | grep -Eq "^tdx-redis\$"; then
        break
    fi
    sleep 1
    done

    # Get the container IP
    REDIS_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' tdx-redis)
    echo "Redis service is started at $REDIS_IP"

    # Wait for redis-server completed work and ready
    count=0
    while true
    do
    redis-cli -h $REDIS_IP ping
    if [[ $? == 0 ]]; then
        echo "Success start redis-server in docker."
        break
    else
        ((count++))
        if (( $count > 10 )); then
            echo "Fail to run redis service after 10 seconds. ret: $ret"
            exit 1
        fi
        echo "redis-server is not ready yet, wait for more seconds..."
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
            /usr/bin/redis-benchmark -h $REDIS_IP -q
        done
    fi

    # Measure
    now=$(date +"%Y_%m_%d-%H_%M_%S")
    for i in `seq $ROUND_NUM`; do
        echo "$i round performance for redis!"
        # Run benchmark
        /usr/bin/redis-benchmark -h $REDIS_IP --csv > ${OUTPUT_DIR}/redis-perf-data-${now}-${i}.txt
        ret=$?
        if [ $ret -eq 0 ];
        then
            echo "Success to run redis service in docker and redis-benchmark"
            sync
            sleep 2
        else
            echo "Fail to run redis benchmark, ret: $ret"
            exit $ret
        fi
    done

    # Output
    cat ${OUTPUT_DIR}/*.txt
}

process_args $@
cleanup
start_redis_server
run_benchmark