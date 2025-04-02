_NOTE: please DO NOT REDISTRIBUTE the prebuilt-binary externally_

_Version: kvm-unit-tests commit 0c259cf369540df8fed7e64d63998f92574966b9_

# get kvm-unit-test
https://gitlab.com/kvm-unit-tests/kvm-unit-tests

# install gcc, make on centos 8.4
sudo dnf install gcc

sudo dnf install make

# build as standalone
cd kvm-unit-tests/

./configure

make standalone

# output dir
./tests/
