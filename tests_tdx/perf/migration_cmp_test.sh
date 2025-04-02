#!/bin/bash

REPEAT_TIME=1

usage() {
    cat << EOM
Usage: $(basename "$0") [OPTION]...
  -i [iteration times]      Iteration/repeat times.
  -f [image file]           The path of the image file.
  -w [work dir]             Top dir of all test scripts.
  -h                        Show this help
EOM
}

process_args() {
    while getopts "i:f:w:h" option; do
        case "${option}" in
            i) REPEAT_TIME=$OPTARG;;
            f) IMAGE_FILE=$OPTARG;;
            w) WORK_DIR=$OPTARG;;
            h) usage
               exit 0
               ;;
            *)
               echo "Invalid option '-$OPTARG'"
               usage
               exit 1
               ;;
        esac
    done
}

run_test() {
    local cpu_count=$1
    local mem_size=$2
    local tdx_enable=$3
    local repeat_times=$4
    echo tdx_enable=${tdx_enable} cpu_count=${cpu_count} mem_size=${mem_size}
    local n=0
    for ((n=0;n<${repeat_times};n++)); do
        echo iteration $n
        setsid -w ${WORK_DIR}/tests_tdx/perf/migration_single_host_test.sh -i $IMAGE_FILE -c ${cpu_count} -m ${mem_size} -x ${tdx_enable} -t ${WORK_DIR}/tdx-tools/utils/td-migration
	sleep 30
    done
}


test_legacy_vm() {
    local repeat_times=$1
    run_test 1 4 false $repeat_times
    run_test 2 8 false $repeat_times
    run_test 4 16 false $repeat_times
    run_test 8 32 false $repeat_times
}

test_td_vm() {
    local repeat_times=$1
    run_test 1 4 true $repeat_times
    run_test 2 8 true $repeat_times
    run_test 4 16 true $repeat_times
    run_test 8 32 true $repeat_times
}

date

process_args "$@"
test_legacy_vm $REPEAT_TIME
test_td_vm $REPEAT_TIME

date
