#!/bin/bash

set +e  # not quit for failure command

# By default, use the same directory as this script as output directory
OUTPUT_DIR=$(dirname "$(readlink -f "$0")")
LOOP=20

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

run_benchmark() {
    now=$(date +"%Y_%m_%d-%H_%M_%S")

    # Warm
    docker run --name reuse tdx_docker/hello:sh
    for i in `seq 20`
    do
	    docker start reuse
    done

    # Run benchmark
    for i in `seq $LOOP`
    do
	    (time docker start reuse) 2>> ${OUTPUT_DIR}/container-start-perf-data-${now}.txt
	    sync
    done

    # Output
    cat ${OUTPUT_DIR}/*.txt

    docker rm reuse

    # Output the average result
    awk '/real/ {print $2}' ${OUTPUT_DIR}/container-start-perf-data-${now}.txt |
    awk -F m '{if ($1==0) print substr($2, 0, 5)}' |
    awk 'BEGIN { sum=0 } { sum+=$1 } END {print "Average container start up time: ", sum/NR }'
}

process_args $@
run_benchmark
