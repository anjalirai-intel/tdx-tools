#!/bin/bash
#
# Read memory from a vm guest.
# Parameters:
#   $1: monitor port
#   $2: format, like /10i
#   $3: address like0xffffffff81000000
#
# @author: cpio
#

check_parameter() 
{ 
    if [ "X$1" == "X" ]; then
        echo "Parameter $2 is empty" 1>&2; 
        exit 1
    fi
}

MONITOR_PORT=$1
FORMAT=$2
ADDRESS=$3

check_parameter $MONITOR_PORT "MONITOR_PORT"
check_parameter $FORMAT "FORMAT"
check_parameter $ADDRESS "ADDRESS"

# sed '1,2d': delete the first two lines (binary)
# sed '$d': delete the last line: (qemu)
echo "x ${FORMAT} ${ADDRESS}" | nc -w 10 localhost ${MONITOR_PORT}  | sed '1,2d' | sed '$d'
exit $?
