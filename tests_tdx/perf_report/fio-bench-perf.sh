#!/bin/bash

set +e  # not quit for failure command

# By default, use the same directory as this script as output directory
OUTPUT_DIR=$(dirname "$(readlink -f "$0")")
LOOP=1

echo "[global]
ioengine=libaio
iodepth=64
size=1g
direct=1
buffered=0
numjobs=8
startdelay=5

ramp_time=5
runtime=20
time_based
disk_util=0
clat_percentiles=0
disable_lat=1
disable_clat=1
disable_slat=1
filename=fiofile
[test]
name=test
bs=4k
stonewall" > test.fio

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

    # Run fio benchmark: read
    for i in `seq $LOOP`
    do
        echo "==== Start Read Loop ${i} ====" >> ${OUTPUT_DIR}/fio-perf-data-read-${now}.txt
        fio --rw=read test.fio >> ${OUTPUT_DIR}/fio-perf-data-read-${now}.txt
	rm fiofile
        echo "==== End Read Loop ${i} ====" >> ${OUTPUT_DIR}/fio-perf-data-read-${now}.txt
	sync
    done

    # Run fio benchmark: write
    for i in `seq $LOOP`
    do
        echo "==== Start Write Loop ${i} ====" >> ${OUTPUT_DIR}/fio-perf-data-write-${now}.txt
        fio --rw=write test.fio >> ${OUTPUT_DIR}/fio-perf-data-write-${now}.txt
	rm fiofile
        echo "==== End Write Loop ${i} ====" >> ${OUTPUT_DIR}/fio-perf-data-write-${now}.txt
	sync
    done

    # Output the raw results
    cat ${OUTPUT_DIR}/*.txt

    sync

    # Output Average result
    awk '/read: IOPS=/ {print $2}' ${OUTPUT_DIR}/fio-perf-data-read-${now}.txt |
    awk -F = '{print $2}' | awk -F k '{print $1}' |
    awk 'BEGIN { sum=0 } { sum+=$1 } END {print "Average read IOPS: ", sum/NR }'

    awk '/write: IOPS=/ {print $2}' ${OUTPUT_DIR}/fio-perf-data-write-${now}.txt |
    awk -F = '{print $2}' | awk -F k '{print $1}' |
    awk 'BEGIN { sum=0 } { sum+=$1 } END {print "Average write IOPS: ", sum/NR }'
}

process_args $@
run_benchmark
