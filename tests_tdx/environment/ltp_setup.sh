#!/bin/bash
# This script sets up the Linux Test Project (LTP) environment for testing.
# It installs the necessary dependencies and builds the LTP from source.
set -x
git clone https://github.com/linux-test-project/ltp.git
cd ltp
ACTION="*" .ci/debian.sh
make autotools
./configure
make -j

# install LTP inside /opt/ltp by default
make install