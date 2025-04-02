#!/bin/bash

TCP_PORT=9001
VSOCK=1234

usage() {
    cat << EOM
Usage: $(basename "$0") [OPTION]...
  -t TCP port value
  -v VSOCK value
  -h Show this
EOM
    exit 0
}

process_args() {
    while getopts ":t:v:h" option; do
        case "${option}" in
            t) TCP_PORT=${OPTARG};;
            v) VSOCK=${OPTARG};;
            h) usage;;
        esac
    done

}

connect() {
    modprobe vhost_vsock
    socat TCP4-LISTEN:${TCP_PORT},reuseaddr VSOCK-LISTEN:${VSOCK},fork &
    sleep 3
    socat TCP4-CONNECT:127.0.0.1:${TCP_PORT},reuseaddr VSOCK-LISTEN:$((VSOCK+1)),fork &
}

process_args $@
connect
