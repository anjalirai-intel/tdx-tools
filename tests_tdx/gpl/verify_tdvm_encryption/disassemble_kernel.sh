#!/bin/bash
#
# Disassemble a kernel file
# Parameters:
#   $1: the output file
#
# @author: cpio
#

echo_stderr()
{
    echo "$@" 1>&2;
}

DEC_FILE=/tmp/kernel.extracted
DIS_FILE=$1

if [ "X${DIS_FILE}" == "X" ]; then
    echo_stderr "invalid parameter"
    exit 1
fi

# Check if extract-linux already downloaded, else grab it from Linux master repo
if [ ! -f ./extract-vmlinux ]; then
    wget -O extract-vmlinux https://raw.githubusercontent.com/torvalds/linux/master/scripts/extract-vmlinux
    if [ $? -ne 0 ]; then
        echo_stderr "failed to download extract-vmlinux script"
        exit 1
    fi
fi

chmod +x extract-vmlinux

# Extract kernel file
KERNEL=$2
echo "./extract-vmlinux ${KERNEL} > ${DEC_FILE}"
./extract-vmlinux ${KERNEL} > ${DEC_FILE}
if [ $? -ne 0 ]; then
    echo_stderr "extract-vmlinuz failed"
    exit 1
fi

# Disassemble the kernel
objdump -d ${DEC_FILE} > ${DIS_FILE}

EXIT_CODE=$?
rm -f ${DEC_FILE}
exit ${EXIT_CODE}
