
"""
Implement the VMMBase via QMP(Qemu Monitor Protocol) which provided from https://pypi.org/project/qmp/.

QMP is under GPL, so all test cases using this module should also under GPL license.


                      +---------+         +---------+
                      | VMMBase |  <----> | VMGuest |
                      +---------+         +---------+
    +------------+       ^   ^        +---------+
    | VMMLibvirt |-------|   |--------| VMMQemu |
    +------------+                    +---------+

"""

import logging
import threading
import subprocess
import time
import random
import re
import qmp

from pycloudstack.vmm import VMMBase
from pycloudstack.dut import DUT
from pycloudstack.cmdrunner import NativeCmdRunner
from pycloudstack.vmparam import VM_TYPE_LEGACY, VM_TYPE_EFI, VM_TYPE_TD, VM_TYPE_SGX, \
    VM_STATE_SHUTDOWN, BOOT_TYPE_DIRECT, BIOS_BINARY_LEGACY_UBUNTU, \
    BIOS_BINARY_LEGACY_CENTOS, BIOS_OVMF, VM_TYPE_MIGTD, MIGTD_DISK_IMAGE


LOG = logging.getLogger(__name__)

ARP_INTERVAL = 120

class VMMQemu(VMMBase):

    """
    QEMU VMM operator.

    It implemented all abstracted interface from the virtual class VMMBase.
    The qemu-kvm process will be managed in standaone thread.
    """

    def __init__(self, vminst, serial_stdio=False, mac_addr=None):
        super().__init__(vminst)
        self._qemu_proc_obj = None
        self._qmp_socket = "/tmp/vm-" + self.vminst.vmid
        self._qmp = None
        self._serial_stdio = serial_stdio
        self._monitor_port = 9011
        self._ip = None

    @property
    def monitor_port(self):
        """
        The port for Qemu monitor.
        """
        return self._monitor_port

    def create(self, stop_at_begining=True):    # noqa: C901
        """
        Create a VM.

        If stop_at_begining is True, then the VM will paused/stopped
        after creation, until execute start() explicity.
        """

        # Qemu command varies in different distro
        # Get distro from /etc/os-release. If it doesn't exist,
        # fall back to /usr/lib/os-release
        distro = DUT.get_distro()

        if "ubuntu" not in distro:
            cmdarr = ["/usr/libexec/qemu-kvm", ]
        else:
            cmdarr = ["/usr/bin/qemu-system-x86_64", ]

        # Stop VM after creation
        if stop_at_begining:
            cmdarr += ["-S", ]

        # common
        cmdarr += ["-accel", "kvm", "-no-hpet", "-nodefaults", "-nographic"]
        cmdarr += ["-name", f"process={self.vminst.name},debug-threads=on"]
        cmdarr += ["-m", f"{self.vminst.vmspec.memsize}K"]
        cmdarr += ["-qmp", f"unix:{self._qmp_socket},server=on,wait=off"]

        # virt-console
        if self._serial_stdio:
            cmdarr += [
                "-chardev", "stdio,id=mux,mux=on,logfile=vm_log2.log",
                "-device", "virtio-serial,romfile=",
                "-device", "virtconsole,chardev=mux",
                "-serial", "chardev:mux",
            ]

        # CPU topology
        cmdarr += [
            "-smp",
            f"{self.vminst.vmspec.vcpus},sockets={self.vminst.vmspec.sockets},"
            f"cores={self.vminst.vmspec.cores},threads={self.vminst.vmspec.threads}"
        ]

        # VM image
        if self.vminst.vmtype is VM_TYPE_MIGTD:
            cmdarr += ["-serial", "mon:stdio"]
            cmdarr += ["-device", "vhost-vsock-pci,id=vhost-vsock-pci1," +
                       f"guest-cid={random.randint(10,999)},disable-legacy=on"]
        else:
            cmdarr += ["-object", "iothread,id=iothread1"]
            cmdarr += ["-drive",
                       f"file={self.vminst.image.filepath},if=none,"
                       "id=virtio-disk,format=qcow2,cache=none,aio=native"]
            cmdarr += ["-device", "virtio-blk-pci,drive=virtio-disk,iothread=iothread1"]
        param_machine = "q35,kernel_irqchip=split"
        param_cpu = "host,-kvm-steal-time,pmu=off"
        if DUT.get_cpu_base_freq() < 1000000:
            param_cpu += ",tsc-freq=1000000000"

        # Bios file
        if self.vminst.vmtype in [VM_TYPE_TD, VM_TYPE_MIGTD]:
            param_machine += ",confidential-guest-support=tdx,memory-backend=ram1"
            if self.vminst.vmtype is VM_TYPE_MIGTD:
                cmdarr += ["-bios", f"{MIGTD_DISK_IMAGE}"]
                cmdarr += ["-object", "tdx-guest,sept-ve-disable=on,id=tdx,quote-generation-service=vsock:1:4050"]
            else:
                cmdarr += ["-bios", f"{BIOS_OVMF}"]
                if self.vminst.migtd_pid is not None and self.vminst.mig_hash is None:
                    cmdarr += ["-object", f"tdx-guest,sept-ve-disable=on,id=tdx,migtd-pid={self.vminst.migtd_pid}"]
                    # Ensure migratable user TD to have the same tsc-freq
                    param_cpu += ",tsc-freq=1000000000"                    
                elif self.vminst.mig_hash is not None:
                    cmdarr += ["-object", f"tdx-guest,sept-ve-disable=on,id=tdx,migtd-hash={self.vminst.mig_hash}"]
                    # Ensure migratable user TD to have the same tsc-freq
                    param_cpu += ",tsc-freq=1000000000"
                else:
                    cmdarr += ["-object", "tdx-guest,sept-ve-disable=on,id=tdx"]
            cmdarr += ["-object", f"memory-backend-memfd-private,id=ram1,size={self.vminst.vmspec.memsize}K"]
            param_cpu += ",-shstk"
            if self.vminst.tsx is False:
                param_cpu += ",-hle,-rtm"
            if self.vminst.tsc is False:
                param_cpu += ",-tsc-deadline"
        elif self.vminst.vmtype is VM_TYPE_EFI:
            cmdarr += ["-bios", f"{BIOS_OVMF}"]
        elif self.vminst.vmtype is VM_TYPE_LEGACY:
            if "ubuntu" not in distro:
                cmdarr += [
                    "-bios", BIOS_BINARY_LEGACY_CENTOS
                ]
            else:
                cmdarr += [
                    "-bios", BIOS_BINARY_LEGACY_UBUNTU
                ]
        elif self.vminst.vmtype is VM_TYPE_SGX:
            if "ubuntu" not in distro:
                cmdarr += [
                    "-bios", BIOS_BINARY_LEGACY_CENTOS
                ]
            else:
                cmdarr += [
                    "-bios", BIOS_BINARY_LEGACY_UBUNTU
                ]
            # sgx config
            sgx_epc = ""
            num = 0
            for section in self.vminst.vmspec.epc:
                num += 1
                prealloc = ",prealloc=on" if section['prealloc'] else ""
                cmdarr += ["-object",
                           f"memory-backend-epc,id=mem{num},size={section['size']}{prealloc}"]
                sgx_epc += f"sgx-epc.{num - 1}.memdev=mem{num}"
                sgx_epc += f",sgx-epc.{num - 1}.node={section['node']},"
            cmdarr += ["-M", f"{sgx_epc[:-1]}"]

        # kernel + append for direct boot
        if self.vminst.boot == BOOT_TYPE_DIRECT and self.vminst.vmtype is not VM_TYPE_MIGTD:
            cmdarr += ["-kernel", self.vminst.kernel]
            cmdarr += ["-append", f"\"{self.vminst.cmdline}\""]

        # Forward SSH port
        if self.vminst.vmtype is not VM_TYPE_MIGTD:
            # generate random mac address
            if self.vminst.mac_addr is None:
                self.vminst.mac_addr = '00:16:3e:68:' + f'{random.randint(0, 255):02x}:{random.randint(0, 255):02x}'
            cmdarr += [
                "-device", f"virtio-net-pci,netdev=mynet0,mac={self.vminst.mac_addr},romfile=",
                "-netdev", "bridge,id=mynet0,br=virbr0"]

        cmdarr += ["-machine", param_machine, "-cpu", param_cpu]

        if self.vminst.incoming_port is not None:
            cmdarr += ["-incoming", f'tcp:0:{self.vminst.incoming_port}']

        # Monitor port
        if self.vminst.vmtype is not VM_TYPE_MIGTD:
            self._monitor_port = DUT.find_free_port()
            cmdarr += ["-monitor", f"telnet:127.0.0.1:{self._monitor_port},server,nowait"]

        # Set MWAIT
        if self.vminst.mwait is not None:
            cmdarr += [f"-overcommit cpu-pm={self.vminst.mwait}"]

        LOG.info(" ".join(cmdarr))

        # Create the qemu-kvm launch thread
        threading.Thread(target=self._qemu_thread, args=(cmdarr, )).start()

        # Wait for qemu-kvm process created
        while self._qemu_proc_obj is None:
            time.sleep(0.5)

        time.sleep(3)  # workaround to wait for qmp socket file created.

        self.vminst.pid = self._qemu_proc_obj.pid

        # create QMP minitor
        self._qmp = qmp.QEMUMonitorProtocol(self._qmp_socket)
        self._qmp.connect()

    def start(self):
        """
        Start a VM if VM is not started.
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        if not self.is_running():
            self._qmp.cmd("cont")

    def suspend(self):
        """
        Suspend a VM if VM is running
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        self._qmp.cmd("stop")

    def resume(self):
        """
        Resume a VM if VM is stopped/paused
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        self._qmp.cmd("cont")

    def reboot(self):
        """
        Reboot a VM.
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        self._qmp.cmd("system_reset")

    def shutdown(self):
        """
        Shutdown a VM.
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        self._qmp.cmd("system_powerdown")

    def destroy(self, is_undefined=True):
        """
        Destroy a VM.
        """
        if self._qemu_proc_obj is not None:
            try:
                cmdret = self._qmp.cmd("query-status")
                status = cmdret["return"]["status"]
            except Exception:   # pylint: disable=broad-except
                status = VM_STATE_SHUTDOWN
            # Shutdown VM before close QMP socket and process
            if status is not VM_STATE_SHUTDOWN:
                self._qmp.cmd("system_powerdown")
            self._qemu_proc_obj.kill()
        if self._qmp is not None:
            self._qmp.close()

    def delete_log(self):
        """
        Delete VM log.
        """

    def is_running(self):
        """
        Check whether a VM is running
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        cmdret = self._qmp.cmd("query-status")
        return cmdret["return"]["running"]

    def state(self):
        """
        Get VM state
        """
        if self._qemu_proc_obj is None:
            return VM_STATE_SHUTDOWN

        try:
            cmdret = self._qmp.cmd("query-status")
        except Exception:   # pylint: disable=broad-except
            return VM_STATE_SHUTDOWN
        LOG.info(str(cmdret))
        return cmdret["return"]["status"]

    def get_ip(self, force_refresh=False):
        """
        Get VM available IP on virtual or physical bridge
        """
        if (not force_refresh) and (self._ip is not None):
            return self._ip

        tstart = time.time()
        retry = ARP_INTERVAL
        while retry > 0:
            runner = NativeCmdRunner(["arp", "-a"], silent=True)
            runner.runwait()

            for line in runner.stdout:
                if self.vminst.mac_addr not in line:
                    continue
                ipaddr = re.search(
                    r'([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', line)
                self._ip = ipaddr.groups(0)[0]
                break

            if self._ip is not None:
                break
            retry -= 1
            time.sleep(1)

        LOG.debug("IP address of %s: %s (duration: %d seconds)",
                  self.vminst.name, self._ip, time.time() - tstart)
        return self._ip

    def update_kernel_cmdline(self, cmdline):
        """
        Update kernel command line
        """
        self.vminst.cmdline = cmdline

    def update_kernel(self, kernel):
        """
        Update kernel used in vm
        """
        self.vminst.kernel = kernel

    def update_vmspec(self, new_vmspec):
        """
        Update VM spec include CPU topology and memory size
        """
        self.vminst.vmspec = new_vmspec

    def inject_nmi(self):
        """
        Inject NMI to to a virtual machine.
        Reference: https://qemu.readthedocs.io/en/latest/interop/qemu-qmp-ref.html#qapidoc-2179
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        cmdret = self._qmp.cmd("inject-nmi")

        return cmdret

    def pre_migration(self, value=None, pre_binding=False, migtd_pid=None):
        """
        Exec pre-migration tasks
        """
        if self.vminst.vmtype is not VM_TYPE_TD or value is None:
            raise NotImplementedError
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None

        # Bind migtd to user TD before running pre-migration
        if pre_binding:
            if migtd_pid:
                self.bind_migtd(migtd_pid)
            else:
                self.bind_migtd(self.vminst.migtd_pid)
        cmdret = self._qmp.cmd("qom-set", {"path": "/objects/tdx/",
                                           "property": "vsockport",
                                           "value": value})
        return cmdret

    def migrate(self, addr=None, port=None):
        """
        Start migration
        """
        if self.vminst.vmtype is not VM_TYPE_TD:
            raise NotImplementedError
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None

        cmdret = self._qmp.cmd("migrate", {"detach": True,
                                           "uri": f'tcp:{ addr if addr is not None else "localhost"}:'
                                           f'{ port if port is not None else "6666"}'})

        # cmdret = self._qmp.cmd("migrate-start-postcopy")
        return cmdret

    def set_migration_capability(self, capability_list):
        """
        Set migration capability
        """
        if self.vminst.vmtype is not VM_TYPE_TD:
            raise NotImplementedError
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None

        for cap in capability_list:
            cmdret = self._qmp.cmd("migrate-set-capabilities", 
        {"capabilities": [cap]})

        cmdret = self._qmp.cmd("query-migrate-capabilities")
        return cmdret

    def set_migration_parameters(self, param_list):
        """
        Set migration parameters
        """
        if self.vminst.vmtype is not VM_TYPE_TD:
            raise NotImplementedError
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None

        for param in param_list:
            cmdret = self._qmp.cmd("migrate-set-parameters", 
        param)

        cmdret = self._qmp.cmd("query-migrate-parameters")
        return cmdret

    def get_migration_capability(self):
        """
        Get migration capability
        """
        if self.vminst.vmtype is not VM_TYPE_TD:
            raise NotImplementedError
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None

        cmdret = self._qmp.cmd("query-migrate-capabilities")
        return cmdret

    def migrate_postcopy(self):
        """
        Start migration post copy
        """
        if self.vminst.vmtype is not VM_TYPE_TD:
            raise NotImplementedError
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None

        cmdret = self._qmp.cmd("migrate-start-postcopy")

    def wait_for_migrate_done(self):
        """
        Check whether migration is complete
        """
        timeout = 300
        is_complete = False
        total_time = 0
        if self.vminst.vmtype is not VM_TYPE_TD:
            raise NotImplementedError
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        
        while (timeout >= 0 and not is_complete):
            cmdret = self._qmp.cmd("query-migrate")
         
            if cmdret['return']['status'] == 'completed':
                is_complete = True
                total_time = cmdret['return']['total-time']
                break
            else:
                timeout -= 5
                time.sleep(5)

        return [is_complete, total_time]

    def cancel_migration(self):
        """
        Cancel VM migration
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None

        cmdret = self._qmp.cmd("migrate_cancel")
        
        return cmdret

    def bind_migtd(self, migtd_pid):
        """
        Bind TD with migTD
        """
        assert self._qemu_proc_obj is not None
        assert self._qmp is not None
        if self.vminst.vmtype is not VM_TYPE_TD:
            raise NotImplementedError
        cmdret = self._qmp.cmd("qom-set", {"path": "/objects/tdx/",
                                           "property": "migtd-pid",
                                           "value": migtd_pid})
        
        return cmdret

    def _qemu_thread(self, cmdarr):
        """
        Standalone thread to monitor qemu-kvm process object.
        """
        LOG.debug("start qemu-kvm")
        self._qemu_proc_obj = subprocess.Popen(
            " ".join(cmdarr),
            shell=True,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        while self._qemu_proc_obj.poll() is None:
            for line in self._qemu_proc_obj.stdout:
                LOG.debug("  [VM-OUT]: %s", line.strip())
            for line in self._qemu_proc_obj.stderr:
                LOG.debug("  [VM-ERR]: %s", line.strip())
        LOG.debug("qemu-kvm stopped, ret=%d", self._qemu_proc_obj.returncode)
        self._qemu_proc_obj = None

    def __del__(self):
        self.destroy()
