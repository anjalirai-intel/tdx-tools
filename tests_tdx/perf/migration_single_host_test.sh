#!/bin/bash

GUEST_IMG=""
CPU_NUM=2
MEM_SIZE=8
TDX_ENABLE="true"
TD_START_TIMEOUT=150
TD_MIGRATION_TIMEOUT=150

usage() {
    cat << EOM
Usage: $(basename "$0") [OPTION]...
  -i <guest image file>     Guest image file
  -c [cpu number]           CPU number (should be > 0), default 2
  -m [memory size]          Memory size (should be > 0, in giga byte), default 8G
  -x [true|false]           Using TDVM, default true. Non-TD VM if it's false
  -t [tdx-tools path]       Path of tdx-tools
  -h                        Show this help
EOM
}

error() {
    echo -e "\e[1;31mERROR: $*\e[0;0m"
    exit 1
}

is_positive_int() {
    local param=$1
    local is_positive=false
    if [[ $param =~ ^[0-9]+$ ]]; then
        if [[ $param -gt 0 ]]; then
            is_positive=true
        fi
    fi
    echo $is_positive
}

process_args() {
    while getopts "i:c:m:x:t:h" option; do
        case "${option}" in
            i) GUEST_IMG=$OPTARG;;
            c) CPU_NUM=$OPTARG;;
            m) MEM_SIZE=$OPTARG;;
            x) TDX_ENABLE=$OPTARG;;
	    t) TDX_TOOLS_PATH=$OPTARG;;
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

    if [[ ! -f ${GUEST_IMG} ]]; then
        usage
        error "The given image file ${GUEST_IMG} does not exist!"
        error "Please specify correct image file!"
        exit 1
    fi

    if [[ ! -e ${TDX_TOOLS_PATH} ]]; then
        usage
        error "The path for tdx-tools does not exist!"
        error "Please specify correct path!"
        exit 1
    fi

    local cpu_num_valid
    cpu_num_valid=$(is_positive_int "${CPU_NUM}")
    if [[ $cpu_num_valid != true ]]; then
        usage
        error "CPU number should be positive integer"
    fi

    local mem_size_valid
    mem_size_valid=$(is_positive_int "${MEM_SIZE}")
    if [[ $mem_size_valid != true ]]; then
        usage
        error "Memory size should be positive integer"
    fi

    case ${TDX_ENABLE} in
        "true") ;;
        "false") ;;
        *)
            error "Invalid TDX option \"$TDX_ENABLE\", must be [true|false]"
            ;;
    esac
}

set_up() {

    if [[ ${TDX_ENABLE} == "true" ]]; then
        # start migtd
        echo start migtd ...
        sudo ${TDX_TOOLS_PATH}/mig-td.sh -t src > /dev/null 2>&1 &
        sudo ${TDX_TOOLS_PATH}/mig-td.sh -t dst > /dev/null 2>&1 &
    fi

    # start src vm and dst vm
    sleep 3
    echo start src vm and dst vm ...
    local vm_param=" -i ${GUEST_IMG} -b grub -c ${CPU_NUM} -m ${MEM_SIZE}"
    if [[ ${TDX_ENABLE} == "true" ]]; then
        vm_param+=" -q tdvmcall "
    else
        vm_param+=" -x false "
    fi
    sudo ${TDX_TOOLS_PATH}/user-td.sh -t src ${vm_param} > /dev/null 2>&1 &
    sleep 6
    sudo ${TDX_TOOLS_PATH}/user-td.sh -t dst ${vm_param} > /dev/null 2>&1 &
    sleep ${TD_START_TIMEOUT}
}

run_test() {

    if [[ ${TDX_ENABLE} == "true" ]]; then
        # start pre-migration
        sudo ${TDX_TOOLS_PATH}/connect.sh
        sleep 3
        ps -ef | grep socat
        sudo ${TDX_TOOLS_PATH}/pre-mig.sh
        sleep 6
        sudo dmesg | grep migration | tail -5
    fi

    # start migration
    sudo ${TDX_TOOLS_PATH}/mig-flow.sh
    sleep ${TD_MIGRATION_TIMEOUT}

    # check the migration result
    echo
    sudo dmesg | grep migration | tail -5
    echo
    ps -ef | grep qemu
    echo
    echo "info migrate" | sudo nc -U /tmp/qmp-sock-src -w3
    echo
}

tear_down() {
    # terminate all sub processes
    sleep 10
    echo All sub process will be terminated now.
    echo But it may take quite a bit of time after this script exit.
    echo So please wait for a while.
    # current pid, also the pgid, is $$
    current_pgid=$$
    sudo kill -SIGTERM -- -$current_pgid
}

process_args "$@"
set_up
run_test
tear_down
