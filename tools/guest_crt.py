"""Python emulation model for NFS ProStreet MSVCR80.dll IAT Shim Layer.

Mirrors runtime/crt.h and runtime/crt.c, providing unit test verification
for memory shims, string shims, math/FPU intrinsics, C++ constructors,
and IAT binding directly into guest memory.
"""
import ctypes
import math
import re
import struct
import time
from typing import Callable, Dict, List, Optional, Tuple

from tools.build_crt_shims import extract_msvcr80_imports, sanitize_name, EXE_PATH
from tools.guest_memory import GuestMemory

GUEST_CRT_BASE      = 0x00101000
GUEST_COMMODE_ADDR  = GUEST_CRT_BASE + 0x00
GUEST_FMODE_ADDR    = GUEST_CRT_BASE + 0x04
GUEST_INITENV_ADDR  = GUEST_CRT_BASE + 0x08
GUEST_IOB_ADDR      = GUEST_CRT_BASE + 0x10
GUEST_ARGV_STR_ADDR = GUEST_CRT_BASE + 0x80
GUEST_ARGV_TAB_ADDR = GUEST_CRT_BASE + 0x100
GUEST_ENVP_TAB_ADDR = GUEST_CRT_BASE + 0x110
GUEST_TM_ADDR       = GUEST_CRT_BASE + 0x140
GUEST_ASCTIME_ADDR  = GUEST_CRT_BASE + 0x180
GUEST_GETCWD_ADDR   = GUEST_CRT_BASE + 0x200

DISPATCH_TEXT_BASE  = 0x00401000
DISPATCH_TEXT_SIZE  = 0x00567000


class SimulatedCPU:
    """Simulated x86 CPU context matching struct CPU from runtime/cpu.h."""

    def __init__(self, memory: GuestMemory):
        self.mem = memory
        self.eax = 0
        self.ecx = 0
        self.edx = 0
        self.ebx = 0
        self.esp = 0x003FF000
        self.ebp = 0x003FF000
        self.esi = 0
        self.edi = 0
        self.eip = 0

        self.cf = 0
        self.pf = 0
        self.af = 0
        self.zf = 0
        self.sf = 0
        self.of = 0
        self.df = 0

        self.st = [0.0] * 8
        self.top = 0
        self.fcw = 0x037F
        self.fsw = 0
        self.fs_base = 0x00100000

        # Initialize Win32 TEB and TLS layout at fs_base
        self.mem.write_u32(self.fs_base + 0x00, 0xFFFFFFFF)
        self.mem.write_u32(self.fs_base + 0x04, 0x003FF000)
        self.mem.write_u32(self.fs_base + 0x08, 0x00200000)
        self.mem.write_u32(self.fs_base + 0x18, self.fs_base)
        self.mem.write_u32(self.fs_base + 0x20, 0x00001000)
        self.mem.write_u32(self.fs_base + 0x24, 0x00001001)
        self.mem.write_u32(self.fs_base + 0x2C, self.fs_base + 0x100)
        self.mem.write_u32(self.fs_base + 0x30, self.fs_base + 0x1000)
        self.mem.write_u32(self.fs_base + 0x100, self.fs_base + 0x200)

    def push32(self, val: int):
        self.esp = (self.esp - 4) & 0xFFFFFFFF
        self.mem.write_u32(self.esp, val & 0xFFFFFFFF)

    def pop32(self) -> int:
        val = self.mem.read_u32(self.esp)
        self.esp = (self.esp + 4) & 0xFFFFFFFF
        return val

    def fpush(self, val: float):
        self.top = (self.top - 1) & 7
        self.st[self.top] = float(val)

    def fpop(self) -> float:
        val = self.st[self.top]
        self.top = (self.top + 1) & 7
        return val

    def st_get(self, idx: int = 0) -> float:
        return self.st[(self.top + idx) & 7]

    def st_set(self, idx: int, val: float):
        self.st[(self.top + idx) & 7] = float(val)


class GuestCRT:
    """Manages MSVCR80.dll shims and IAT registration."""

    def __init__(self, memory: GuestMemory, exe_bytes: Optional[bytes] = None):
        self.mem = memory
        if exe_bytes is None and EXE_PATH.exists():
            with open(EXE_PATH, 'rb') as f:
                exe_bytes = f.read()

        self.imports = extract_msvcr80_imports(exe_bytes) if exe_bytes else []
        self.dtab: Dict[int, Callable[[SimulatedCPU], None]] = {}
        self.onexit_table: List[int] = []
        self.app_type = 1
        self.files: Dict[int, io_file_entry] = {}

    def init_iat(self):
        """Initializes metadata and binds all 156 IAT slots."""
        # 1. Setup metadata
        self.mem.write_u32(GUEST_COMMODE_ADDR, 0)
        self.mem.write_u32(GUEST_FMODE_ADDR, 0)
        self.mem.write_u32(GUEST_INITENV_ADDR, 0)
        for i in range(96):
            self.mem.write_u8(GUEST_IOB_ADDR + i, 0)

        self.mem.write_bytes(GUEST_ARGV_STR_ADDR, b"nfs.exe\0")
        self.mem.write_u32(GUEST_ARGV_TAB_ADDR, GUEST_ARGV_STR_ADDR)
        self.mem.write_u32(GUEST_ARGV_TAB_ADDR + 4, 0)
        self.mem.write_u32(GUEST_ENVP_TAB_ADDR, 0)

        # 2. Bind IAT slots
        for slot_va, sym in self.imports:
            # Guest reads slot_va from the IAT slot itself
            self.mem.write_u32(slot_va, slot_va)
            handler = self._get_handler(sym)
            offset = slot_va - DISPATCH_TEXT_BASE
            if 0 <= offset < DISPATCH_TEXT_SIZE:
                self.dtab[offset] = handler

    def dispatch_call(self, cpu: SimulatedCPU, target_va: int):
        offset = target_va - DISPATCH_TEXT_BASE
        if offset in self.dtab:
            self.dtab[offset](cpu)
        else:
            raise KeyError(f"Unknown dispatch target: 0x{target_va:08x}")

    def _get_handler(self, sym: str) -> Callable[[SimulatedCPU], None]:
        fn_name = sanitize_name(sym)
        method = getattr(self, fn_name, None)
        if method:
            return method
        return lambda c: setattr(c, 'eax', 0)

    # --------------------------------------------------------------------------
    # Memory Shims
    # --------------------------------------------------------------------------
    def crt_shim_malloc(self, c: SimulatedCPU):
        size = self.mem.read_u32(c.esp)
        c.eax = self.mem.heap_alloc(max(size, 1), 8)

    def crt_shim_free(self, c: SimulatedCPU):
        pass

    def crt_shim_calloc(self, c: SimulatedCPU):
        num = self.mem.read_u32(c.esp)
        size = self.mem.read_u32(c.esp + 4)
        total = num * size
        ptr = self.mem.heap_alloc(max(total, 1), 8)
        self.mem.write_bytes(ptr, b'\0' * total)
        c.eax = ptr

    def crt_shim_realloc(self, c: SimulatedCPU):
        ptr = self.mem.read_u32(c.esp)
        size = self.mem.read_u32(c.esp + 4)
        if not ptr:
            c.eax = self.mem.heap_alloc(max(size, 1), 8)
            return
        if not size:
            c.eax = 0
            return
        nptr = self.mem.heap_alloc(size, 8)
        data = self.mem.read_bytes(ptr, min(size, 4096))
        self.mem.write_bytes(nptr, data)
        c.eax = nptr

    def crt_shim__aligned_malloc(self, c: SimulatedCPU):
        size = self.mem.read_u32(c.esp)
        align = self.mem.read_u32(c.esp + 4)
        c.eax = self.mem.heap_alloc(max(size, 1), align if align else 8)

    def crt_shim__aligned_free(self, c: SimulatedCPU):
        pass

    # --------------------------------------------------------------------------
    # Memory Movement & Strings
    # --------------------------------------------------------------------------
    def crt_shim_memcpy(self, c: SimulatedCPU):
        dst = self.mem.read_u32(c.esp)
        src = self.mem.read_u32(c.esp + 4)
        n = self.mem.read_u32(c.esp + 8)
        if n > 0:
            data = self.mem.read_bytes(src, n)
            self.mem.write_bytes(dst, data)
        c.eax = dst

    def crt_shim_memcpy_s(self, c: SimulatedCPU):
        dst = self.mem.read_u32(c.esp)
        dstsz = self.mem.read_u32(c.esp + 4)
        src = self.mem.read_u32(c.esp + 8)
        count = self.mem.read_u32(c.esp + 12)
        if count > dstsz:
            c.eax = 0x22
            return
        if count > 0:
            data = self.mem.read_bytes(src, count)
            self.mem.write_bytes(dst, data)
        c.eax = 0

    def crt_shim_memmove(self, c: SimulatedCPU):
        self.crt_shim_memcpy(c)

    def crt_shim_memmove_s(self, c: SimulatedCPU):
        self.crt_shim_memcpy_s(c)

    def crt_shim_memset(self, c: SimulatedCPU):
        dst = self.mem.read_u32(c.esp)
        val = self.mem.read_u32(c.esp + 4) & 0xFF
        n = self.mem.read_u32(c.esp + 8)
        if n > 0:
            self.mem.write_bytes(dst, bytes([val] * n))
        c.eax = dst

    def crt_shim_memcmp(self, c: SimulatedCPU):
        s1 = self.mem.read_u32(c.esp)
        s2 = self.mem.read_u32(c.esp + 4)
        n = self.mem.read_u32(c.esp + 8)
        b1 = self.mem.read_bytes(s1, n)
        b2 = self.mem.read_bytes(s2, n)
        c.eax = (b1 > b2) - (b1 < b2)

    def _read_guest_str(self, va: int) -> str:
        s = bytearray()
        while True:
            b = self.mem.read_u8(va)
            if b == 0:
                break
            s.append(b)
            va += 1
        return s.decode('latin1', errors='replace')

    def crt_shim_strlen(self, c: SimulatedCPU):
        s = self._read_guest_str(self.mem.read_u32(c.esp))
        c.eax = len(s)

    def crt_shim_strcpy(self, c: SimulatedCPU):
        dst = self.mem.read_u32(c.esp)
        src = self._read_guest_str(self.mem.read_u32(c.esp + 4))
        self.mem.write_bytes(dst, src.encode('latin1') + b'\0')
        c.eax = dst

    def crt_shim_strcpy_s(self, c: SimulatedCPU):
        dst = self.mem.read_u32(c.esp)
        dstsz = self.mem.read_u32(c.esp + 4)
        src = self._read_guest_str(self.mem.read_u32(c.esp + 8))
        if len(src) + 1 > dstsz:
            c.eax = 0x22
            return
        self.mem.write_bytes(dst, src.encode('latin1') + b'\0')
        c.eax = 0

    def crt_shim_strncpy(self, c: SimulatedCPU):
        dst = self.mem.read_u32(c.esp)
        src = self._read_guest_str(self.mem.read_u32(c.esp + 4))
        n = self.mem.read_u32(c.esp + 8)
        b = src.encode('latin1')[:n]
        if len(b) < n:
            b = b + b'\0' * (n - len(b))
        self.mem.write_bytes(dst, b)
        c.eax = dst

    def crt_shim_strcmp(self, c: SimulatedCPU):
        s1 = self._read_guest_str(self.mem.read_u32(c.esp))
        s2 = self._read_guest_str(self.mem.read_u32(c.esp + 4))
        c.eax = (s1 > s2) - (s1 < s2)

    def crt_shim_strncmp(self, c: SimulatedCPU):
        s1 = self._read_guest_str(self.mem.read_u32(c.esp))
        s2 = self._read_guest_str(self.mem.read_u32(c.esp + 4))
        n = self.mem.read_u32(c.esp + 8)
        s1 = s1[:n]
        s2 = s2[:n]
        c.eax = (s1 > s2) - (s1 < s2)

    def crt_shim__stricmp(self, c: SimulatedCPU):
        s1 = self._read_guest_str(self.mem.read_u32(c.esp)).lower()
        s2 = self._read_guest_str(self.mem.read_u32(c.esp + 4)).lower()
        c.eax = (s1 > s2) - (s1 < s2)

    def crt_shim__strnicmp(self, c: SimulatedCPU):
        n = self.mem.read_u32(c.esp + 8)
        s1 = self._read_guest_str(self.mem.read_u32(c.esp)).lower()[:n]
        s2 = self._read_guest_str(self.mem.read_u32(c.esp + 4)).lower()[:n]
        c.eax = (s1 > s2) - (s1 < s2)

    def crt_shim_strcat(self, c: SimulatedCPU):
        dst_va = self.mem.read_u32(c.esp)
        src = self._read_guest_str(self.mem.read_u32(c.esp + 4))
        dst_str = self._read_guest_str(dst_va)
        new_str = (dst_str + src).encode('latin1') + b'\0'
        self.mem.write_bytes(dst_va, new_str)
        c.eax = dst_va

    def crt_shim_strchr(self, c: SimulatedCPU):
        s_va = self.mem.read_u32(c.esp)
        ch = chr(self.mem.read_u32(c.esp + 4) & 0xFF)
        s = self._read_guest_str(s_va)
        idx = s.find(ch)
        c.eax = s_va + idx if idx >= 0 else 0

    def crt_shim_strstr(self, c: SimulatedCPU):
        h_va = self.mem.read_u32(c.esp)
        h = self._read_guest_str(h_va)
        n = self._read_guest_str(self.mem.read_u32(c.esp + 4))
        idx = h.find(n)
        c.eax = h_va + idx if idx >= 0 else 0

    def crt_shim_atoi(self, c: SimulatedCPU):
        s = self._read_guest_str(self.mem.read_u32(c.esp)).strip()
        try:
            m = re.match(r'^[-+]?\d+', s)
            c.eax = int(m.group(0)) & 0xFFFFFFFF if m else 0
        except Exception:
            c.eax = 0

    def crt_shim_atof(self, c: SimulatedCPU):
        s = self._read_guest_str(self.mem.read_u32(c.esp)).strip()
        try:
            val = float(s)
        except Exception:
            val = 0.0
        c.fpush(val)

    def crt_shim_tolower(self, c: SimulatedCPU):
        ch = self.mem.read_u32(c.esp) & 0xFF
        c.eax = ord(chr(ch).lower())

    def crt_shim_toupper(self, c: SimulatedCPU):
        ch = self.mem.read_u32(c.esp) & 0xFF
        c.eax = ord(chr(ch).upper())

    def crt_shim_isdigit(self, c: SimulatedCPU):
        ch = chr(self.mem.read_u32(c.esp) & 0xFF)
        c.eax = 1 if ch.isdigit() else 0

    def crt_shim_isspace(self, c: SimulatedCPU):
        ch = chr(self.mem.read_u32(c.esp) & 0xFF)
        c.eax = 1 if ch.isspace() else 0

    # --------------------------------------------------------------------------
    # Formatted I/O
    # --------------------------------------------------------------------------
    def crt_shim_sprintf(self, c: SimulatedCPU):
        buf_va = self.mem.read_u32(c.esp)
        fmt = self._read_guest_str(self.mem.read_u32(c.esp + 4))
        arg_ptr = c.esp + 8
        res, _ = self._format_str(fmt, arg_ptr)
        self.mem.write_bytes(buf_va, res.encode('latin1') + b'\0')
        c.eax = len(res)

    def crt_shim_sscanf(self, c: SimulatedCPU):
        src = self._read_guest_str(self.mem.read_u32(c.esp))
        fmt = self._read_guest_str(self.mem.read_u32(c.esp + 4))
        # Support basic %d %d parsing
        tokens = src.split()
        specs = fmt.split()
        matched = 0
        arg_ptr = c.esp + 8
        for s, tok in zip(specs, tokens):
            if s == '%d':
                out_va = self.mem.read_u32(arg_ptr)
                arg_ptr += 4
                self.mem.write_u32(out_va, int(tok) & 0xFFFFFFFF)
                matched += 1
        c.eax = matched

    def _format_str(self, fmt: str, arg_ptr: int) -> Tuple[str, int]:
        out = []
        i = 0
        while i < len(fmt):
            if fmt[i] != '%':
                out.append(fmt[i])
                i += 1
                continue
            i += 1
            if i < len(fmt) and fmt[i] == '%':
                out.append('%')
                i += 1
                continue
            # Read spec
            spec = []
            while i < len(fmt) and fmt[i] not in 'diuoxXcspnfeEgG':
                spec.append(fmt[i])
                i += 1
            conv = fmt[i] if i < len(fmt) else 's'
            i += 1
            spec_str = '%' + ''.join(spec) + conv
            if conv == 's':
                sva = self.mem.read_u32(arg_ptr)
                arg_ptr += 4
                out.append(self._read_guest_str(sva) if sva else "(null)")
            elif conv in 'feEgG':
                # Float argument on stack is 8 bytes
                low = self.mem.read_u32(arg_ptr)
                high = self.mem.read_u32(arg_ptr + 4)
                arg_ptr += 8
                fval = struct.unpack('<d', struct.pack('<II', low, high))[0]
                out.append(spec_str % fval)
            else:
                ival = self.mem.read_u32(arg_ptr)
                arg_ptr += 4
                if conv in 'di':
                    if ival >= 0x80000000:
                        ival -= 0x100000000
                out.append(spec_str % ival)
        return ''.join(out), arg_ptr

    # --------------------------------------------------------------------------
    # Math & FPU Intrinsics
    # --------------------------------------------------------------------------
    def crt_shim__CIsin(self, c: SimulatedCPU):
        c.st_set(0, math.sin(c.st_get(0)))

    def crt_shim__CIcos(self, c: SimulatedCPU):
        c.st_set(0, math.cos(c.st_get(0)))

    def crt_shim__CIsqrt(self, c: SimulatedCPU):
        c.st_set(0, math.sqrt(c.st_get(0)))

    def crt_shim__CItan(self, c: SimulatedCPU):
        c.st_set(0, math.tan(c.st_get(0)))

    def crt_shim__CIasin(self, c: SimulatedCPU):
        c.st_set(0, math.asin(c.st_get(0)))

    def crt_shim__CIacos(self, c: SimulatedCPU):
        c.st_set(0, math.acos(c.st_get(0)))

    def crt_shim__CIatan(self, c: SimulatedCPU):
        c.st_set(0, math.atan(c.st_get(0)))

    def crt_shim__CIexp(self, c: SimulatedCPU):
        c.st_set(0, math.exp(c.st_get(0)))

    def crt_shim__CIlog(self, c: SimulatedCPU):
        c.st_set(0, math.log(c.st_get(0)))

    def crt_shim__CIlog10(self, c: SimulatedCPU):
        c.st_set(0, math.log10(c.st_get(0)))

    def crt_shim__CIpow(self, c: SimulatedCPU):
        y = c.st_get(0)
        x = c.st_get(1)
        c.fpop()
        c.st_set(0, math.pow(x, y))

    def crt_shim__CIatan2(self, c: SimulatedCPU):
        x = c.st_get(0)
        y = c.st_get(1)
        c.fpop()
        c.st_set(0, math.atan2(y, x))

    def crt_shim__CIfmod(self, c: SimulatedCPU):
        y = c.st_get(0)
        x = c.st_get(1)
        c.fpop()
        c.st_set(0, math.fmod(x, y))

    def crt_shim_sin(self, c: SimulatedCPU):
        low = self.mem.read_u32(c.esp)
        high = self.mem.read_u32(c.esp + 4)
        x = struct.unpack('<d', struct.pack('<II', low, high))[0]
        c.fpush(math.sin(x))

    def crt_shim_cos(self, c: SimulatedCPU):
        low = self.mem.read_u32(c.esp)
        high = self.mem.read_u32(c.esp + 4)
        x = struct.unpack('<d', struct.pack('<II', low, high))[0]
        c.fpush(math.cos(x))

    def crt_shim_sqrt(self, c: SimulatedCPU):
        low = self.mem.read_u32(c.esp)
        high = self.mem.read_u32(c.esp + 4)
        x = struct.unpack('<d', struct.pack('<II', low, high))[0]
        c.fpush(math.sqrt(x))

    def crt_shim_floor(self, c: SimulatedCPU):
        low = self.mem.read_u32(c.esp)
        high = self.mem.read_u32(c.esp + 4)
        x = struct.unpack('<d', struct.pack('<II', low, high))[0]
        c.fpush(math.floor(x))

    def crt_shim_ceil(self, c: SimulatedCPU):
        low = self.mem.read_u32(c.esp)
        high = self.mem.read_u32(c.esp + 4)
        x = struct.unpack('<d', struct.pack('<II', low, high))[0]
        c.fpush(math.ceil(x))

    def crt_shim_abs(self, c: SimulatedCPU):
        v = self.mem.read_u32(c.esp)
        if v >= 0x80000000:
            v = (-v) & 0xFFFFFFFF
        c.eax = v

    def crt_shim__isnan(self, c: SimulatedCPU):
        low = self.mem.read_u32(c.esp)
        high = self.mem.read_u32(c.esp + 4)
        x = struct.unpack('<d', struct.pack('<II', low, high))[0]
        c.eax = 1 if math.isnan(x) else 0

    # --------------------------------------------------------------------------
    # Initializers & Control Flow
    # --------------------------------------------------------------------------
    def register_onexit(self, fn_va: int) -> int:
        self.onexit_table.append(fn_va)
        return fn_va

    def get_onexit_count(self) -> int:
        return len(self.onexit_table)

    def crt_shim__initterm(self, c: SimulatedCPU):
        start = self.mem.read_u32(c.esp)
        end = self.mem.read_u32(c.esp + 4)
        for p in range(start, end, 4):
            fn_va = self.mem.read_u32(p)
            if fn_va != 0:
                saved_esp = c.esp
                self.dispatch_call(c, fn_va)
                c.esp = saved_esp

    def crt_shim__initterm_e(self, c: SimulatedCPU):
        start = self.mem.read_u32(c.esp)
        end = self.mem.read_u32(c.esp + 4)
        for p in range(start, end, 4):
            fn_va = self.mem.read_u32(p)
            if fn_va != 0:
                saved_esp = c.esp
                self.dispatch_call(c, fn_va)
                c.esp = saved_esp
                if c.eax != 0:
                    return
        c.eax = 0

    def crt_shim__onexit(self, c: SimulatedCPU):
        fn_va = self.mem.read_u32(c.esp)
        self.onexit_table.append(fn_va)
        c.eax = fn_va

    def crt_shim___dllonexit(self, c: SimulatedCPU):
        fn_va = self.mem.read_u32(c.esp)
        self.onexit_table.append(fn_va)
        c.eax = fn_va

    def crt_shim__encode_pointer(self, c: SimulatedCPU):
        c.eax = self.mem.read_u32(c.esp)

    def crt_shim__decode_pointer(self, c: SimulatedCPU):
        c.eax = self.mem.read_u32(c.esp)

    def crt_shim___getmainargs(self, c: SimulatedCPU):
        p_argc = self.mem.read_u32(c.esp)
        p_argv = self.mem.read_u32(c.esp + 4)
        p_envp = self.mem.read_u32(c.esp + 8)
        if p_argc:
            self.mem.write_u32(p_argc, 1)
        if p_argv:
            self.mem.write_u32(p_argv, GUEST_ARGV_TAB_ADDR)
        if p_envp:
            self.mem.write_u32(p_envp, GUEST_ENVP_TAB_ADDR)
        c.eax = 0

    def crt_shim___set_app_type(self, c: SimulatedCPU):
        self.app_type = self.mem.read_u32(c.esp)
        c.eax = 0

    def crt_shim___p__commode(self, c: SimulatedCPU):
        c.eax = GUEST_COMMODE_ADDR

    def crt_shim___p__fmode(self, c: SimulatedCPU):
        c.eax = GUEST_FMODE_ADDR

    def crt_shim___iob_func(self, c: SimulatedCPU):
        c.eax = GUEST_IOB_ADDR

    def crt_shim__setjmp3(self, c: SimulatedCPU):
        env_va = self.mem.read_u32(c.esp)
        self.mem.write_u32(env_va + 0, c.ebp)
        self.mem.write_u32(env_va + 4, c.ebx)
        self.mem.write_u32(env_va + 8, c.edi)
        self.mem.write_u32(env_va + 12, c.esi)
        self.mem.write_u32(env_va + 16, c.esp)
        self.mem.write_u32(env_va + 20, c.eip)
        c.eax = 0

    def crt_shim_longjmp(self, c: SimulatedCPU):
        env_va = self.mem.read_u32(c.esp)
        val = self.mem.read_u32(c.esp + 4)
        c.ebp = self.mem.read_u32(env_va + 0)
        c.ebx = self.mem.read_u32(env_va + 4)
        c.edi = self.mem.read_u32(env_va + 8)
        c.esi = self.mem.read_u32(env_va + 12)
        c.esp = self.mem.read_u32(env_va + 16)
        c.eip = self.mem.read_u32(env_va + 20)
        c.eax = val if val else 1


class io_file_entry:
    def __init__(self, path: str):
        self.path = path
        self.pos = 0
