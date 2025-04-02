# Stability How-To

## Explanation

Stability tests should not be ran with `./run.sh -s stability`, as they are long-running and may cause issues on the host. Instead, they should be ran individually with some extra manual logging enabled.

## Serial logging
Ensure that the serial port of the host system is being logged via the cpio-debugger-prc1. The command looks like this: `minicom -D /dev/ttyUSBX -C logfile.txt`. Replace X and logfile appropriately.

## Running the stability test
If you are SSH'd into the host, its recommended to run the stability test in a tmux session in case you are disconnected: `tmux`

While in the tmux session, run the chosen stability test while also logging to a file: `./run.sh -c tests_tdx/stability/test_chosen_test.py 2>&1 | tee -a logfile.txt`. Replace chosen test and logfile appropriately.
