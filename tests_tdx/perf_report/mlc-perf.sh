#!/bin/bash

set -ex

CURR_DIR=$(dirname $(readlink -f "$0"))
MLC_URL="http://cpio-build-prc1.sh.intel.com/mirror/mlc/mlc_v3.9a.tgz"
MLC_FILENAME="${MLC_URL##*/}"
MLC_DIR="${CURR_DIR}/mlc"
WARMUP_NUM=2
ROUND_NUM=3
now=$(date +"%Y_%m_%d-%H_%M_%S")
OUTPUT=${CURR_DIR}/mlc-report
RESULT_FILE_NAME="${OUTPUT}/mlc-result-${now}.txt"

download_mlc() {
    if [[ ! -d ${MLC_DIR}/Linux ]]; then
        if [[ ! -f ${CURR_DIR}/${MLC_FILENAME} ]]; then
            wget ${MLC_URL} -O ${CURR_DIR}/${MLC_FILENAME}
        fi

        mkdir -p ${MLC_DIR}
        cd ${MLC_DIR} && tar xf ${CURR_DIR}/${MLC_FILENAME}
    fi
}

run_mlc() {
    echo $*
    RESULT_FILE_NAME="${OUTPUT}/mlc-result-${1}-${RANDOM}-${now}.txt"

    if (( $WARMUP_NUM > 0 )); then
        echo "Warm up ..."
        for i in `seq $WARMUP_NUM`; do
            echo "  Warmup - $i times"
            sync
            echo 3 > /proc/sys/vm/drop_caches
            ${MLC_DIR}/Linux/mlc ${@:2}
        done
    fi

    mkdir -p ${OUTPUT}
    for i in `seq $ROUND_NUM`; do
        echo "$i round performance for mlc!"
        # Run benchmark
        echo ">> Round: [$i] <<" >> ${RESULT_FILE_NAME}
        sync
        echo 3 > /proc/sys/vm/drop_caches

        ${MLC_DIR}/Linux/mlc ${@:2} >> ${RESULT_FILE_NAME}
        ret=$?
        if [ $ret -eq 0 ];
        then
            echo "Success to run mlc"
            sync
            sleep 1
        else
            echo "Fail to run mlc, ret: $ret"
            exit $ret
        fi
    done
}

download_mlc
run_mlc $*
