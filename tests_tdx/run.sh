#!/bin/bash

CURR_DIR=$(readlink -f $(dirname "$0"))
TEST_ROOT=${CURR_DIR}
TEST_OUTPUT=${CURR_DIR}/output
USER=$(whoami)
REPORT_FILE_DATE=$(date +'report-%F-%H-%M-%S')
REPORT_DIR_NAME=$(date +'%F')
HOST=$(cat /proc/sys/kernel/hostname)
GUEST=ubuntu
SUITE="nosuite"
NO_UPLOAD=false
KEEP_ISSUE_VM=false
CASES=()
PARALLEL='no'
MAX_FAILURES=0
CPU_FREQUENCY=2500000
KUBECONFIG=""

usage() {
cat << EOM
Usage: $(basename "$0") [OPTION]...
  -s Test suite in bat|stability|functional|perf,  like "-s bat"
  -c Multiple options for individual cases file like "-c tests_tdx/environment/test_tdvm_ltp.py"
  -n Not upload
  -i set kubeconfig path
  -k Keep unhealthy VM
  -g Set Guest OS type
  -p pararallel <n|auto>
  -f cpu frequency for performance test, default value is 2500000
  -m <n> max failures: stop testing after <n> failures
  -h Show this
EOM
    exit 0
}

process_args() {

    while getopts "s:c:i:g:f:nkhp:m:" opt; do
        case $opt in
        s) SUITE="$OPTARG"
           [[ ! $SUITE =~ smoke|bat|regression|functional|stability|perf_reg|perf_report|pts|environment|lifecycle|gpl|interoperability|kubevirt|nontme ]] && {
               echo "Incorrect suite name $SUITE provided."
               exit 1
           }
           ;;
        c) CASES+=("$OPTARG");;
        n) NO_UPLOAD=true;;
        k) KEEP_ISSUE_VM=true;;
        i) KUBECONFIG=$OPTARG;;
        g) GUEST="$OPTARG"
            [[ ! $GUEST =~ rhel|centos|centosstream|ubuntu ]] && {
               echo "Incorrect guest name $GUEST provided."
               exit 1
           }
           ;;
        p) PARALLEL="$OPTARG"
           if [ $PARALLEL != 'auto' ]; then
               if ! [[ ${PARALLEL} =~ ^[0-9]+$ && ${PARALLEL} -gt 0 ]]; then
                   echo "Invalid value \"$PARALLEL\" for parallel processing argument '-p'."
                   echo "Expected 'auto' or a number of tests to be executed in parallel."
                   exit 1
               fi
           fi
           ;;
        m) MAX_FAILURES="$OPTARG"
           if ! [[ ${MAX_FAILURES} =~ ^[0-9]+$ && ${MAX_FAILURES} -gt 0 ]]; then
               echo "Invalid value \"$MAX_FAILURES\" for max failures argument '-m'."
               echo "Expected a positive number."
               exit 1
           fi
           ;;
        f) CPU_FREQUENCY="$OPTARG"
            if ! [[ ${CPU_FREQUENCY} =~ ^[0-9]+$ ]]; then
                echo "Invalid value \"$CPU_FREQUENCY\"."
                exit 1
            fi
            ;;
        h) usage;;
        esac
    done

    if [  $SUITE != "nosuite" ] && [ ${#CASES[@]} != 0 ]; then
        echo "Do not specify the case(-c) and suite(-s) at same time."
        exit 1
    fi

    SUFFIX=${HOST}-${GUEST}-${USER}-${REPORT_FILE_DATE}

}

upload() {
    if [[ -f ${CURR_DIR}/tools/upload_report.sh ]]; then
        ${CURR_DIR}/tools/upload_report.sh $1 /${HOST}/${REPORT_DIR_NAME}
    fi
}

perf_preset() {
    # set cpu frequency to specific value
    sudo cpupower frequency-set --max ${CPU_FREQUENCY} --min ${CPU_FREQUENCY} > /dev/null
    if [[ $? -ne 0 ]]; then
        echo "Fail to fix CPU frequency to ${CPU_FREQUENCY}."
        exit 1
    fi

    # Validate whether the value is set successfully
    CPU_MAX_FREQ=`cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq`
    CPU_MIN_FREQ=`cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq`
    for max in $CPU_MAX_FREQ
    do
        if [ ${max} -ne ${CPU_FREQUENCY} ]; then
            echo "Not all cpu max frequency set to ${CPU_FREQUENCY}! Please check the value."
            exit 1
        fi
    done

    for min in $CPU_MIN_FREQ
    do
        if [ ${min} -ne ${CPU_FREQUENCY} ]; then
            echo "Not all cpu min frequency set to ${CPU_FREQUENCY}! Please check the value."
            exit 1
        fi
    done

    # set cpu governor to performance
    sudo cpupower frequency-set -g performance > /dev/null
    if [[ $? -ne 0 ]]; then
        echo "Fail to set CPU governance mode to performance."
        exit 1
    fi

    # Validate whether the governor is set successfully
    CPU_GOVERNOR=`cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`
    for gov in $CPU_GOVERNOR
    do
        if [ ${gov} != "performance" ]; then
            echo "Not all cpu governor set to 'performance'! Please check the value."
            exit 1
        fi
    done

    echo "===============Run Pre-set for performance tests=================="
    echo "CPU max frequency  : ${CPU_FREQUENCY}"
    echo "CPU min frequency  : ${CPU_FREQUENCY}"
    echo "CPU governance  : performance"
    echo "===============End of Pre-set for performance tests=================="
}

run_suite() {

    HTML_REPORT=${TEST_OUTPUT}/${SUITE}-${SUFFIX}.html
    if [  $KEEP_ISSUE_VM == true ]; then
        PYTEST_PREFIX="python3 -m pytest --html=${HTML_REPORT} --self-contained-html --keep-vm --guest=$GUEST"
    else
        PYTEST_PREFIX="python3 -m pytest --html=${HTML_REPORT} --self-contained-html --guest=$GUEST"
    fi

    case $SUITE in
    smoke)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT} -m smoke"
        ;;
    bat)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT} -m bat"
        ;;
    regression)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT} -m regression"
        ;;
    nontme)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT} -m nontme"
        ;;
    stability)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/stability"
        ;;
    perf_reg)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/perf"
        perf_preset
        ;;
    perf_report)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/perf_report"
        perf_preset
        ;;
    pts)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/perf/test_pts.py"
        ;;
    gpl)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/gpl"
        ;;
    functional)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/workload ${TEST_ROOT}/environment ${TEST_ROOT}/lifecycle ${TEST_ROOT}/gpl"
        PYTEST_CMD+=" ${TEST_ROOT}/perf/test_perf_fio_regression.py ${TEST_ROOT}/perf/test_pts.py::test_pts_postgresql"
        PYTEST_CMD+=" ${TEST_ROOT}/td_migration ${TEST_ROOT}/vtpm"
        PYTEST_CMD+=" ${TEST_ROOT}/td_attest"
        ;;
    environment)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/environment"
        ;;
    lifecycle)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/lifecycle"
        ;;
    interoperability)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/interoperability"
        ;;
    kubevirt)
        PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT}/kubevirt"
        ;;
    esac

    if [ ${PARALLEL} != 'no' ]; then
        PYTEST_CMD+=" -n ${PARALLEL}"
    fi

    if [[ ${MAX_FAILURES} -gt 0 ]]; then
        PYTEST_CMD+=" --maxfail=${MAX_FAILURES}"
    fi

    if [ ! -z "$KUBECONFIG" ]; then
        PYTEST_CMD+=" --kubeconfig ${KUBECONFIG}"
    fi

    echo "================================="
    echo "RUN Suite  : $SUITE"
    echo "CMD        : $PYTEST_CMD"
    echo "No Upload  : $NO_UPLOAD"
    echo "Keep Issue VM    : $KEEP_ISSUE_VM"
    echo "Guest      : $GUEST"
    echo "Parallel   : $PARALLEL"
    echo "================================="

    eval $PYTEST_CMD

    if [ $NO_UPLOAD == false ] && [ -f ${HTML_REPORT} ]; then
        upload ${HTML_REPORT}
    fi
}

run_cases() {

    HTML_REPORT=${TEST_OUTPUT}/${SUITE}-${SUFFIX}.html
    if [  $KEEP_ISSUE_VM == true ]; then
        PYTEST_PREFIX="python3 -m pytest --html=${HTML_REPORT} --self-contained-html --keep-vm --guest=$GUEST"
    else
        PYTEST_PREFIX="python3 -m pytest --html=${HTML_REPORT} --self-contained-html --guest=$GUEST"
    fi
    PYTEST_CMD="${PYTEST_PREFIX} $(printf " %s" "${CASES[@]}")"

    if [ ${PARALLEL} != 'no' ]; then
        PYTEST_CMD+=" -n ${PARALLEL}"
    fi

    if [ ! -z "$KUBECONFIG" ]; then
        PYTEST_CMD+=" --kubeconfig ${KUBECONFIG}"
    fi

    if [[ ${MAX_FAILURES} -gt 0 ]]; then
        PYTEST_CMD+=" --maxfail=${MAX_FAILURES}"
    fi

    if [[ $PYTEST_CMD == *"perf"* ]]; then
        perf_preset
    fi

    echo "================================="
    echo "CMD        : $PYTEST_CMD"
    echo "No Upload  : $NO_UPLOAD"
    echo "Keep Issue VM    : $KEEP_ISSUE_VM"
    echo "Guest      : $GUEST"
    echo "Parallel   : $PARALLEL"
    echo "================================="

    eval $PYTEST_CMD

    if [ $NO_UPLOAD == false ] && [ -f ${HTML_REPORT} ]; then
        upload ${HTML_REPORT}
    fi

}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "The tests must run under root."
        exit 1
    fi
}

process_args $@

source ${CURR_DIR}/setupenv.sh

if [[ $SUITE != "nosuite" ]]; then
    if [[ $SUITE =~ bat|stability|lifecycle ]]; then
        check_root
    fi
    run_suite
else
    run_cases
fi