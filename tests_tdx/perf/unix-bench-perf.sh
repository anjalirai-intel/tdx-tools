#!/bin/bash

set -ex

CURR_DIR=$(dirname $(readlink -f "$0"))
SRC_URL="https://github.com/kdlucas/byte-unixbench.git"
SRC_DIR="${CURR_DIR}/byte-unixbench"
now=$(date +"%Y_%m_%d-%H_%M_%S")
OUTPUT_DIR=$(dirname "$(readlink -f "$0")")
LOOP=1

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

install_unixbench() {
    if [[ ! -d ${SRC_DIR} ]]; then
        git clone ${SRC_URL} ${SRC_DIR}
    fi

    cd ${SRC_DIR}/UnixBench && make
}

run_unixbench() {
    RESULT_FILE_NAME="${OUTPUT_DIR}/unixbench-${now}.txt"

    for i in `seq $LOOP`; do
        echo "$i round performance for UnixBench!"
        # Run benchmark
        echo ">> Round: [$i] <<" >> ${RESULT_FILE_NAME}
        sync
        echo 3 > /proc/sys/vm/drop_caches

        ${SRC_DIR}/UnixBench/Run >> ${RESULT_FILE_NAME}
        ret=$?
        if [ $ret -eq 0 ];
        then
            echo "Success to run UnixBench"
            sync
            sleep 1
        else
            echo "Fail to run UnixBench, ret: $ret"
            exit $ret
        fi
    done
}

process_args $@
install_unixbench
run_unixbench $*
