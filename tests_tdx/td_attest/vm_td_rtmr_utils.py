"""
This is a utils that runs in the TDVM environment to call ioctl to write extend
data into RTMR registers

Sample:
1. write to rtmr:
    python3 /root/pytdxattest/vm_td_rtmr_utils.py -e <EXTEND_DATA>
    python3 /root/pytdxattest/vm_td_rtmr_utils.py -e <EXTEND_DATA> -r <RTMR_REGISTER>
    python3 /root/pytdxattest/vm_td_rtmr_utils.py -e <EXTEND_DATA> -r <RTMR_REGISTER> -f <OUTPUT_FILE>

"""

import logging
import argparse
import fcntl
import os
import struct
import pickle
from pytdxattest.rtmr import RTMR

LOG = logging.getLogger(__name__)
RTMR_EXTEND_OUTPUT_FILE = '/tmp/test-rtmr.log'
TDX_EXTEND_RTMR_DATA_LEN = 48

logging.basicConfig(level=logging.DEBUG, format='%(message)s')

def extend_rtmr_register(extend_data, rtmr_register, output_filename):
    rtmr_response = RTMR.extend_rtmr(extend_data, None, None, rtmr_register)
    outfile = open(output_filename, 'wb')
    pickle.dump(rtmr_response, outfile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The utility to write data into RTMR register")
    parser.add_argument('-e', type=str, help='Extend value to rtmr register', dest='rtmr_extend_data')
    parser.add_argument('-r', type=int, default=2, help='RTMR register to extend', dest='extended_rtmr_register')
    parser.add_argument('-f', default=RTMR_EXTEND_OUTPUT_FILE,
                        help='File to store rtmr extend result', dest='rtmr_extend_output_file')

    args = parser.parse_args()
    print(args)
    '''
    FIXME:
    '''
    if args.rtmr_extend_data is not None:
        extend_rtmr_register(args.rtmr_extend_data, args.extended_rtmr_register, args.rtmr_extend_output_file)
