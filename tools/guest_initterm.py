"""Need for Speed ProStreet - Static Initializer Chain & MSVC Hook Simulator.

Provides table discovery, execution of C initializers (__xi_a..__xi_z) and
960 C++ constructors (__xc_a..__xc_z), and atexit / __onexit registration.
"""
from typing import List, Optional, Callable, Dict
from tools.guest_memory import GuestMemory
from tools.guest_crt import GuestCRT, SimulatedCPU, DISPATCH_TEXT_BASE, DISPATCH_TEXT_SIZE
from tools.guest_win32 import GuestWin32

# Authentic virtual address ranges in nfs.exe .rdata
GUEST_XI_A            = 0x0096a1f8
GUEST_XI_Z            = 0x0096a204
GUEST_XC_A            = 0x00967608
GUEST_XC_Z            = 0x0096a1f4
GUEST_SUB_0082851B    = 0x0082851b
GUEST_TOTAL_CPP_CTORS = 960


class GuestInitterm:
    """Manages static initializer tables and MSVC constructor boot sequence."""

    def __init__(self, memory: GuestMemory, crt: GuestCRT, win32: Optional[GuestWin32] = None):
        self.mem = memory
        self.crt = crt
        self.win32 = win32

    def install_hooks(self):
        """Installs the authentic atexit / __onexit helper hook into dispatch table."""
        def hook_sub_0082851b(c: SimulatedCPU):
            dtor_va = self.mem.read_u32(c.esp)
            self.crt.register_onexit(dtor_va)
            c.eax = 0  # 0 indicates success in atexit contract

        offset = GUEST_SUB_0082851B - DISPATCH_TEXT_BASE
        if 0 <= offset < DISPATCH_TEXT_SIZE:
            self.crt.dtab[offset] = hook_sub_0082851b

    def get_c_initializers(self) -> List[int]:
        """Returns all non-null entries in the C initializers table (__xi_a .. __xi_z)."""
        entries = []
        for p in range(GUEST_XI_A, GUEST_XI_Z, 4):
            fn_va = self.mem.read_u32(p)
            if fn_va != 0:
                entries.append(fn_va)
        return entries

    def get_cpp_constructors(self) -> List[int]:
        """Returns all non-null entries in the C++ constructors table (__xc_a .. __xc_z)."""
        entries = []
        for p in range(GUEST_XC_A, GUEST_XC_Z, 4):
            fn_va = self.mem.read_u32(p)
            if fn_va != 0:
                entries.append(fn_va)
        return entries

    def run_c_initializers(self, cpu: SimulatedCPU) -> int:
        """Executes C initializers via _initterm_e. Returns 0 on success."""
        saved_esp = cpu.esp
        cpu.push32(GUEST_XI_Z)
        cpu.push32(GUEST_XI_A)
        self.crt.crt_shim__initterm_e(cpu)
        cpu.esp = saved_esp
        return cpu.eax

    def run_cpp_constructors(self, cpu: SimulatedCPU) -> int:
        """Executes all C++ static constructors via _initterm. Returns count executed."""
        saved_esp = cpu.esp
        cpu.push32(GUEST_XC_Z)
        cpu.push32(GUEST_XC_A)
        self.crt.crt_shim__initterm(cpu)
        cpu.esp = saved_esp
        return len(self.get_cpp_constructors())

    def run_exit_destructors(self, cpu: SimulatedCPU):
        """Runs all registered atexit / onexit destructors in LIFO order."""
        while len(self.crt.onexit_table) > 0:
            fn_va = self.crt.onexit_table.pop()
            if fn_va != 0:
                saved_esp = cpu.esp
                self.crt.dispatch_call(cpu, fn_va)
                cpu.esp = saved_esp

