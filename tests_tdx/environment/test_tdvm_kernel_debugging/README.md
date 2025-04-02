# kernel debugging manual test in tdx guest

## test
- download a tdx guest image from http://cpio-devops-pub.sh.intel.com/download/tdx-guest/latest/
- ./start-qemu.sh -i td-guest-centos8.4-test-nosig.qcow2 -k bzImage
- check vm_log_**.log or dmesg with keyword "cpio"
- bzImage is prebuilt. It can be built following below steps.

## source
- git clone --depth 1 --branch tdx-guest-v5.14-5 https://github.com/intel/tdx.git
- cd tdx
- cp -r tdvm_debug drivers/
- git am 0001-tdvm-kernel-debugging-unittest.patch

## build
- sudo dnf -y install make gcc elfutils-libelf-devel
- cp .config to root dir (tdx guest kernel config)
- make bzImage -j8
- copy arch/x86/boot/bzImage
