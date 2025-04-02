"""
This is a utils that runs in the TDVM environment to fetch CCEL
data, replay the eventlogs and save the result in file.

Sample:
1. fetch CCEL data:
    python3 /root/pytdxattest/vm_td_ccel_utils.py -f <OUTPUT_FILE>

"""

import logging
import argparse
import base64
import pickle
from pytdxattest.ccel import CCEL
from pytdxattest.actor import TDEventLogActor
from pytdxattest.tdreport import TdReport

LOG = logging.getLogger(__name__)
CCEL_REPLAY_OUTPUT_FILE = '/tmp/ccel-replay-rtmr.log'
TD_REPORT_OUTPUT_FILE = '/tmp/td_report_f1.bin'

logging.basicConfig(level=logging.DEBUG, format='%(message)s')

def fetch_data_and_replay_rtmr_values(output_ccel_filename, output_report_filename):
    outfile = open(output_ccel_filename, 'w')
    ccelobj = CCEL.create_from_acpi_file()
    if ccelobj is None:
        outfile.write("")
        return

    td_event_log_actor = TDEventLogActor(
            ccelobj.log_area_start_address,
            ccelobj.log_area_minimum_length)
    td_event_log_actor.replay()
    for x in range(4):
        ccel_rtmr = td_event_log_actor.get_rtmr_by_index(x)
        ccel_string = base64.b64encode(ccel_rtmr.data).decode("utf-8")
        outfile.write(ccel_string + '\n')

    if output_report_filename is None:
        return

    td_report_obj = TdReport.get_td_report()
    report_file = open(output_report_filename, 'wb')
    pickle.dump(td_report_obj, report_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The utility to fetch CCEL data and replay RTMR values")
    parser.add_argument('-c', default=CCEL_REPLAY_OUTPUT_FILE,
                        help='File to store rtmr values replayed from ccel eventlogs', dest='ccel_output_file')
    parser.add_argument('-r', default=TD_REPORT_OUTPUT_FILE,
                        help='File to store td report', dest='td_report_output_file')

    args = parser.parse_args()
    print(args)
    '''
    FIXME:
    '''
    fetch_data_and_replay_rtmr_values(args.ccel_output_file, args.td_report_output_file)
