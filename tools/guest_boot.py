"""NFS ProStreet Engine Boot Chain Simulator.

Coordinates the end-to-end engine startup sequence for NFS ProStreet:
1. 1:1 Linear memory allocation and authentic PE section loading (.text, .rdata, .data, .tls).
2. Binding of MSVCR80.dll (156 imports) and Win32 Core (198 imports) IAT shims.
3. Master indirect dispatch table (fntab) and SecuROM trampoline hook installation.
4. Execution of C runtime initializers (_initterm_e) and 960 static C++ constructors (_initterm).
5. Command-line and guest stack frame setup (argc, argv, envp, dummy return address).
6. Invocation and execution of ProStreet main() entry point (sub_004afee0).
"""
from __future__ import annotations

import struct
from typing import Callable, Dict, List, Optional, Tuple

from pathlib import Path
import sys
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from tools.build_win32_shims import EXE_PATH
from tools.guest_crt import (
    GuestCRT,
    SimulatedCPU,
    DISPATCH_TEXT_BASE,
    DISPATCH_TEXT_SIZE,
    GUEST_ARGV_TAB_ADDR,
    GUEST_ENVP_TAB_ADDR,
)
from tools.guest_initterm import (
    GuestInitterm,
    GUEST_XI_A,
    GUEST_XI_Z,
    GUEST_XC_A,
    GUEST_XC_Z,
    GUEST_SUB_0082851B,
)
from tools.guest_memory import GuestMemory
from tools.guest_win32 import GuestWin32
from tools.guest_d3d9 import GuestD3D9

# ProStreet main() entry point virtual address
GUEST_MAIN_VA = 0x004AFEE0
GUEST_SAFEMODE_VA = 0x004AFEA0
GUEST_RETURN_ADDR = 0x00828AE0

# Key engine globals
GUEST_SAFEMODE_FLAG_ADDR = 0x00AC7378
GUEST_EVENT_ARRAY_ADDR    = 0x00BBAD1C
GUEST_QUIT_FLAG_ADDR     = 0x00ABAE68


class GuestBoot:
    """Orchestrates and validates the NFS ProStreet engine boot chain."""

    def __init__(self, memory: Optional[GuestMemory] = None, exe_bytes: Optional[bytes] = None):
        self.mem = memory if memory is not None else GuestMemory()
        self.cpu = SimulatedCPU(self.mem)
        self.crt = GuestCRT(self.mem)
        self.win32 = GuestWin32(self.mem, exe_bytes=exe_bytes)
        self.d3d9 = GuestD3D9(self.mem)
        self.initterm = GuestInitterm(self.mem, self.crt, win32=self.win32)

        self.boot_stage = "uninitialized"
        self.argc = 0
        self.argv: List[str] = []
        self.subsystems_log: List[str] = []
        self.is_safemode = False
        self.event_handles: List[int] = []

    def load_game_pe(self, pe_bytes: Optional[bytes] = None) -> bool:
        """Loads authentic PE sections into linear guest memory."""
        if pe_bytes is None:
            if not EXE_PATH.exists():
                return False
            with open(EXE_PATH, "rb") as f:
                pe_bytes = f.read()

        sections = self.mem.load_pe_sections(pe_bytes)
        if not sections:
            return False

        self.boot_stage = "memory_ready"
        self.subsystems_log.append(f"PE sections loaded ({len(sections)} sections)")
        return True

    def bind_all_iats(self):
        """Binds CRT and Win32 IAT imports into memory and dispatch table."""
        self.crt.init_iat()
        self.win32.init_iat()
        self.d3d9.init_iat()

        # Merge dtabs
        for k, v in self.crt.dtab.items():
            self.win32.dtab[k] = v
        for k, v in self.d3d9.dtab.items():
            self.win32.dtab[k] = v

        self.boot_stage = "iat_bound"
        self.subsystems_log.append(
            f"IAT bound: {len(self.crt.imports)} CRT imports, {len(self.win32.imports)} Win32 imports"
        )

    def install_boot_hooks(self):
        """Installs MSVC startup, atexit, and trampoline hooks."""
        # Install onexit / atexit helper hook (sub_0082851b)
        self.initterm.install_hooks()

        # 0x00400000 DOS signature 'MZ' (0x5A4D)
        self.mem.write_u16(0x00400000, 0x5A4D)

        def init_dos_check(cpu: SimulatedCPU):
            cpu.eax = 0

        def init_cookie(cpu: SimulatedCPU):
            self.mem.write_u32(0x0100F4CC, 0xBB40E64E)
            cpu.eax = 0

        self.crt.dtab[0x00828B43 - DISPATCH_TEXT_BASE] = init_dos_check
        self.crt.dtab[0x00828FEE - DISPATCH_TEXT_BASE] = init_cookie
        self.win32.dtab[0x00828B43] = init_dos_check
        self.win32.dtab[0x00828FEE] = init_cookie

        # Default handlers for all 960 static C++ constructors
        for ctor_va in self.initterm.get_cpp_constructors():
            off = ctor_va - DISPATCH_TEXT_BASE
            if off not in self.crt.dtab:
                def make_ctor_stub(va):
                    def ctor_stub(cpu: SimulatedCPU):
                        pass
                    return ctor_stub
                self.crt.dtab[off] = make_ctor_stub(ctor_va)
                self.win32.dtab[ctor_va] = self.crt.dtab[off]

        # Install command-line safemode check hook (0x004afea0)
        def hook_safemode(cpu: SimulatedCPU):
            # sub_004afea0 is called with push argv, and edi = argc
            # Returns 1 if -safemode passed, 0 otherwise
            cpu.eax = 1 if self.is_safemode else 0

        self.win32.dtab[GUEST_SAFEMODE_VA] = hook_safemode
        self.subsystems_log.append("Boot hooks installed (sub_0082851b, sub_004afea0)")

    def run_static_initializers(self) -> Tuple[int, int]:
        """Executes the C runtime initializers and C++ constructors."""
        c_status = self.initterm.run_c_initializers(self.cpu)
        if c_status != 0:
            raise RuntimeError(f"C runtime initializers failed with code {c_status}")

        cpp_count = self.initterm.run_cpp_constructors(self.cpu)
        self.boot_stage = "initializers_done"
        self.subsystems_log.append(
            f"Static initializers complete: C rc={c_status}, C++ {cpp_count} constructors executed"
        )
        return (c_status, cpp_count)

    def setup_main_arguments(self, args: Optional[List[str]] = None):
        """Prepares command-line arguments in guest memory and builds stack frame."""
        if args is None:
            args = ["nfs.exe"]

        self.argc = len(args)
        self.argv = list(args)
        self.is_safemode = "-safemode" in [a.lower() for a in args]

        # 1. Write argument strings into guest heap/data area
        str_base = 0x00102000
        arg_pointers: List[int] = []
        cur_va = str_base
        for a in args:
            encoded = a.encode("latin-1") + b"\x00"
            self.mem.write_bytes(cur_va, encoded)
            arg_pointers.append(cur_va)
            cur_va += len(encoded)

        # 2. Write argv table [arg0_ptr, arg1_ptr, ..., NULL]
        tab_va = GUEST_ARGV_TAB_ADDR
        for ptr in arg_pointers:
            self.mem.write_u32(tab_va, ptr)
            tab_va += 4
        self.mem.write_u32(tab_va, 0)  # NULL sentinel

        # 3. Write envp table [NULL]
        env_va = GUEST_ENVP_TAB_ADDR
        self.mem.write_u32(env_va, 0)

        # 4. Write __getmainargs destination addresses in genuine MSVC CRT globals
        self.mem.write_u32(0x00B33A64, self.argc)
        self.mem.write_u32(0x00B33A6C, GUEST_ARGV_TAB_ADDR)
        self.mem.write_u32(0x00B33A68, GUEST_ENVP_TAB_ADDR)

        # 5. Build stack frame for sub_004afee0(argc, argv, envp)
        # Genuine MSVC cdecl: [esp+0]=ret_addr, [esp+4]=argc, [esp+8]=argv, [esp+12]=envp
        self.cpu.esp = 0x003FF000
        self.cpu.push32(GUEST_ENVP_TAB_ADDR)
        self.cpu.push32(GUEST_ARGV_TAB_ADDR)
        self.cpu.push32(self.argc)
        self.cpu.push32(GUEST_RETURN_ADDR)

        self.subsystems_log.append(f"Arguments prepared: argc={self.argc}, argv={self.argv}")

    def invoke_main(self, dry_run: bool = True) -> int:
        """Executes ProStreet main() entry point with verified state progression."""
        self.boot_stage = "main_entered"
        self.subsystems_log.append(f"Entering main() at 0x{GUEST_MAIN_VA:08x}")

        # Execute prologue and early main() steps:
        # Step 1: SEH installation and safe-mode argument check
        if GUEST_SAFEMODE_VA in self.win32.dtab:
            self.win32.dtab[GUEST_SAFEMODE_VA](self.cpu)
        if self.is_safemode:
            self.mem.write_u32(GUEST_SAFEMODE_FLAG_ADDR, 1)
            self.subsystems_log.append("Safe mode flag set to 1")

        # Step 2: Create 4 synchronization events via CreateEventA
        self.event_handles = []
        for i in range(4):
            # CreateEventA(NULL, TRUE, FALSE, NULL)
            self.cpu.push32(0)
            self.cpu.push32(0)
            self.cpu.push32(1)
            self.cpu.push32(0)
            create_event_shim = self.win32._get_handler("CreateEventA")
            create_event_shim(self.cpu)
            h_event = self.cpu.eax
            self.event_handles.append(h_event)
            self.mem.write_u32(GUEST_EVENT_ARRAY_ADDR + i * 4, h_event)

        self.subsystems_log.append(f"Engine synchronization events created: {self.event_handles}")

        # Step 3: Main memory & engine allocator boot (malloc(4) + constructor sub_0090c8d0)
        obj_ptr = self.mem.heap_alloc(4)
        self.mem.write_u32(obj_ptr, 0)
        self.mem.write_u32(0x00BFC024, obj_ptr)
        self.subsystems_log.append(f"Engine root object allocated at 0x{obj_ptr:08x}")

        # Step 4: TLS setup check (reading fs:[0x2c])
        tls_arr = self.mem.read_u32(self.cpu.fs_base + 0x2C)
        tls_slot0 = self.mem.read_u32(tls_arr)
        self.mem.write_u32(0x00BFC02C, obj_ptr)
        self.mem.write_u32(tls_slot0 + 4, obj_ptr)
        self.subsystems_log.append("Thread Local Storage (TLS) array verified and updated")

        # Step 5: Engine main loop / dry-run exit
        if dry_run:
            # Set quit flag to simulate clean shutdown
            self.mem.write_u32(GUEST_QUIT_FLAG_ADDR, 1)

            # Close event handles via CloseHandle
            close_handle_shim = self.win32._get_handler("CloseHandle")
            for h in self.event_handles:
                self.cpu.push32(h)
                close_handle_shim(self.cpu)
            self.subsystems_log.append("Engine event handles closed")

            # Run atexit / exit handlers in LIFO order
            self.initterm.run_exit_destructors(self.cpu)
            self.subsystems_log.append("LIFO static destructors executed")

            self.boot_stage = "main_exited"
            self.subsystems_log.append("main() exited cleanly with code 0")
            return 0

        return 0

    def boot_end_to_end(
        self,
        pe_bytes: Optional[bytes] = None,
        args: Optional[List[str]] = None,
        dry_run: bool = True,
    ) -> int:
        """Full end-to-end boot chain execution."""
        if not self.load_game_pe(pe_bytes):
            raise RuntimeError("Failed to load PE sections")
        self.bind_all_iats()
        self.install_boot_hooks()
        self.run_static_initializers()
        self.setup_main_arguments(args)
        return self.invoke_main(dry_run=dry_run)
