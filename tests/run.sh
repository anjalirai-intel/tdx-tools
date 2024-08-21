#!/bin/bash

CURR_DIR="$(readlink -f "$(dirname "$0")")"
TEST_ROOT=${CURR_DIR}/tests
TEST_OUTPUT=${CURR_DIR}/output
USER=$(whoami)
REPORT_FILE_DATE=$(date +'report-%F-%H-%M-%S')
HOST=$(cat /proc/sys/kernel/hostname)
GUEST=ubuntu
SUITE="nosuite"
KEEP_ISSUE_VM=false
CASES=()
PYTEST_EXCLUDE_TESTS="-k 'not redis and not nginx and not amx'"

usage() {
cat << EOM
Usage: $(basename "$0") [OPTION]...
  -s Run all tests
  -c Multiple options for individual cases file like "-c tests/test_vm_coexist.py"
  -k Keep unhealthy VM
  -g Choice Guest OS type from ["rhel", "centosstream", "ubuntu"], default is Ubuntu
  -h Show this
EOM
    exit 0
}

process_args() {

    while getopts "c:g:skh" opt; do
        case $opt in
        s) SUITE="all";;
        c) CASES+=("$OPTARG");;
        k) KEEP_ISSUE_VM=true;;
        g) GUEST="$OPTARG"
            [[ ! $GUEST =~ ^(rhel|centosstream|ubuntu)$ ]] && {
               echo "Incorrect guest name $GUEST provided, must be rhel, centosstream or ubuntu."
               exit 1
           }
           ;;
        h) usage;;
        *) usage;;
        esac
    done

    if [  $SUITE != "nosuite" ] && [ ${#CASES[@]} != 0 ]; then
        echo "Do not specify the case(-c) and suite(-s) at same time."
        exit 1
    fi
    SUFFIX=${HOST}-${GUEST}-${USER}-${REPORT_FILE_DATE}

}

run_suite() {

    XML_REPORT=${TEST_OUTPUT}/${SUITE}-${SUFFIX}.xml
    if [  $KEEP_ISSUE_VM == true ]; then
        PYTEST_PREFIX="python3 -m pytest --reruns 2 --junit-xml=${XML_REPORT} --keep-vm --guest=$GUEST"
    else
        PYTEST_PREFIX="python3 -m pytest --reruns 2 --junit-xml=${XML_REPORT} --guest=$GUEST"
    fi

    PYTEST_CMD="${PYTEST_PREFIX} ${TEST_ROOT} ${PYTEST_EXCLUDE_TESTS}"

    echo "================================="
    echo "RUN Suite  : $SUITE"
    echo "CMD        : $PYTEST_CMD"
    echo "Keep Issue VM    : $KEEP_ISSUE_VM"
    echo "================================="

    eval "$PYTEST_CMD"
}

run_cases() {

    XML_REPORT=${TEST_OUTPUT}/${SUITE}-${SUFFIX}.xml
    if [  $KEEP_ISSUE_VM == true ]; then
        PYTEST_PREFIX="python3 -m pytest --reruns 2 --junit-xml=${XML_REPORT} --keep-vm --guest=$GUEST"
    else
        PYTEST_PREFIX="python3 -m pytest --reruns 2 --junit-xml=${XML_REPORT} --guest=$GUEST"
    fi
    PYTEST_CMD="${PYTEST_PREFIX} $(printf " %s" "${CASES[@]}") ${PYTEST_EXCLUDE_TESTS}"

    echo "================================="
    echo "CMD        : $PYTEST_CMD"
    echo "Keep Issue VM    : $KEEP_ISSUE_VM"
    echo "================================="

    eval "$PYTEST_CMD"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "The tests must run under root."
        exit 1
    fi
}

check_prerequistes() {
    if [[ ! -f ${CURR_DIR}/artifacts.yaml ]]; then
        echo "Please create artifacts.yaml from template file ${CURR_DIR}/artifacts.yaml.template first".
        exit 1
    fi
}

process_args "$@"

# shellcheck source=/dev/null
source "${CURR_DIR}"/setupenv.sh

check_prerequistes
check_root

if [[ $SUITE != "nosuite" ]]; then
    run_suite
else
    run_cases
fi
