#!/bin/bash
#
# Make swapfile in a vm guest.
# Parameters:
#   $1: swapfile size
#
# @author: cpio
#

if [ $# -ne 1 ]; then
    count=2048
else
    count=$1
fi

if [ -f /swapfile ]; then
    swapoff /swapfile
    rm -rf /swapfile
fi

dd if=/dev/zero of=/swapfile bs=1M count=${count}
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
exit $?