"""
This is a utils that runs in the TDVM environment to call tdx measure tool package,
get td-report and save it to as a file. # pylint: disable=line-too-long

Sample:
1. get td-report and save it to a binary file:
    python3 /root/pytdxattest/vm_td_report_utils.py -s <FILENAME>
    python3 /root/pytdxattest/vm_td_report_utils.py -s <FILENAME> -i <REPORTDATA>
2. get td-report with multi-threads
    python3 /root/pytdxattest/vm_td_report_utils.py -m <NOF_THREADS> <FILENAME>
    python3 /root/pytdxattest/vm_td_report_utils.py -m <NOF_THREADS> <FILENAME> -i <REPORTDATA>
3. dump a td report binary file:
    python3 /root/pytdxattest/vm_td_report_utils.py -d <FILENAME>
"""

import logging
import pickle
import argparse
import threading
import time
from pytdxattest.tdreport import TdReport

LOG = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG, format='%(message)s')


def save_td_report_to_file(output_filename, report_data=None):
    """
    Save td-report to a file
    """
    if report_data is not None:
        td_report_obj = TdReport.get_td_report(report_data.encode())
    else:
        td_report_obj = TdReport.get_td_report()
    outfile = open(output_filename, 'wb')
    pickle.dump(td_report_obj, outfile)


def parse_td_report_file(td_report_filename):
    """
    Parse a file to td-report object and dump it
    """
    infile = open(td_report_filename, 'rb')
    td_report_obj = pickle.load(infile)
    infile.close()
    td_report_obj.dump()


def thrd_get_td_report(cv, tr_id, filename, report_data):
    """
    A thread which blocked by a cv
    """
    with cv:
        cv.wait()
        save_td_report_to_file("%s-%d" % (filename, tr_id), report_data)


def thrd_notifier(cv):
    """
    A thread used to notify all blocked threads
    """
    with cv:
        cv.notifyAll()


def mp_get_report(nof_process, filename, report_data=None):
    condition = threading.Condition()
    cs_list = []
    for i in range(nof_process):
        tr_thread = threading.Thread(name='thrd_get_td_report-%d' % (i), target=thrd_get_td_report,
                                     args=(condition, i, filename, report_data))
        cs_list.append(tr_thread)

    pd = threading.Thread(name='thrd_notifier', target=thrd_notifier, args=(condition,))

    for i in range(nof_process):
        cs_list[i].start()
        time.sleep(2)
    pd.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', help='Get td-report and save to <FILE>', dest='td_obj_file_name')
    group.add_argument('-m', nargs=2, help='number of thread to get td report',
                       dest='mp_test')
    group.add_argument('-d', help='Dump a td-report object file', dest='td_report_filename')
    parser.add_argument('-i', help='Set td-report data', dest='input_report_data')

    args = parser.parse_args()
    print(args)
    '''
    FIXME:
    '''
    if args.td_obj_file_name is not None:
        save_td_report_to_file(args.td_obj_file_name, args.input_report_data)
    if args.td_report_filename is not None:
        parse_td_report_file(args.td_report_filename)
    if args.mp_test is not None:
        mp_get_report(int(args.mp_test[0]), args.mp_test[1], args.input_report_data)
