"""Unit and integration tests for MSVCR80.dll IAT Shim Layer.

Validates memory allocation, string operations, math/FPU intrinsics,
C++ static constructors, and 156-slot IAT dispatch binding.
"""
import math
import struct
import unittest
from pathlib import Path

from tools.guest_memory import GuestMemory
from tools.guest_crt import (
    GuestCRT,
    SimulatedCPU,
    GUEST_ARGV_STR_ADDR,
    GUEST_ARGV_TAB_ADDR,
    GUEST_COMMODE_ADDR,
    GUEST_FMODE_ADDR,
    GUEST_IOB_ADDR,
    DISPATCH_TEXT_BASE,
)
from tools.build_crt_shims import extract_msvcr80_imports, EXE_PATH, sanitize_name


class TestCrtShimUnit(unittest.TestCase):
    def setUp(self):
        self.mem = GuestMemory()
        self.crt = GuestCRT(self.mem, exe_bytes=None)
        self.cpu = SimulatedCPU(self.mem)

    def test_malloc_and_free(self):
        self.cpu.esp = 0x003FF000
        self.cpu.push32(128)  # size = 128
        self.crt.crt_shim_malloc(self.cpu)
        self.assertGreaterEqual(self.cpu.eax, 0x02000000)
        self.assertEqual(self.cpu.eax % 8, 0)

        # Free is safe no-op
        self.cpu.push32(self.cpu.eax)
        self.crt.crt_shim_free(self.cpu)

    def test_calloc_and_realloc(self):
        self.cpu.esp = 0x003FF000
        self.cpu.push32(4)    # size = 4
        self.cpu.push32(16)   # num = 16 (64 bytes total)
        self.crt.crt_shim_calloc(self.cpu)
        ptr = self.cpu.eax
        self.assertGreaterEqual(ptr, 0x02000000)
        # Verify zero-initialized
        zero_bytes = self.mem.read_bytes(ptr, 64)
        self.assertEqual(zero_bytes, b'\0' * 64)

        # Realloc to 128 bytes
        self.mem.write_bytes(ptr, b'TESTDATA')
        self.cpu.esp = 0x003FF000
        self.cpu.push32(128)  # new size
        self.cpu.push32(ptr)  # old ptr
        self.crt.crt_shim_realloc(self.cpu)
        new_ptr = self.cpu.eax
        self.assertGreaterEqual(new_ptr, 0x02000000)
        self.assertEqual(self.mem.read_bytes(new_ptr, 8), b'TESTDATA')

    def test_aligned_malloc(self):
        self.cpu.esp = 0x003FF000
        self.cpu.push32(64)   # alignment = 64
        self.cpu.push32(256)  # size = 256
        self.crt.crt_shim__aligned_malloc(self.cpu)
        self.assertEqual(self.cpu.eax % 64, 0)

    def test_string_helpers(self):
        str_va = self.mem.heap_alloc(64, 4)
        self.mem.write_bytes(str_va, b"Need For Speed\0")

        # strlen
        self.cpu.esp = 0x003FF000
        self.cpu.push32(str_va)
        self.crt.crt_shim_strlen(self.cpu)
        self.assertEqual(self.cpu.eax, 14)

        # strcpy
        dst_va = self.mem.heap_alloc(64, 4)
        self.cpu.esp = 0x003FF000
        self.cpu.push32(str_va)
        self.cpu.push32(dst_va)
        self.crt.crt_shim_strcpy(self.cpu)
        self.assertEqual(self.mem.read_bytes(dst_va, 15), b"Need For Speed\0")

        # strcmp / _stricmp
        other_va = self.mem.heap_alloc(64, 4)
        self.mem.write_bytes(other_va, b"need for speed\0")
        self.cpu.esp = 0x003FF000
        self.cpu.push32(other_va)
        self.cpu.push32(str_va)
        self.crt.crt_shim__stricmp(self.cpu)
        self.assertEqual(self.cpu.eax, 0)

        # strstr
        self.cpu.esp = 0x003FF000
        needle_va = self.mem.heap_alloc(16, 4)
        self.mem.write_bytes(needle_va, b"Speed\0")
        self.cpu.push32(needle_va)
        self.cpu.push32(str_va)
        self.crt.crt_shim_strstr(self.cpu)
        self.assertEqual(self.cpu.eax, str_va + 9)

        # atoi
        num_va = self.mem.heap_alloc(16, 4)
        self.mem.write_bytes(num_va, b"2007\0")
        self.cpu.esp = 0x003FF000
        self.cpu.push32(num_va)
        self.crt.crt_shim_atoi(self.cpu)
        self.assertEqual(self.cpu.eax, 2007)

        # atof
        float_va = self.mem.heap_alloc(16, 4)
        self.mem.write_bytes(float_va, b"3.14159\0")
        self.cpu.esp = 0x003FF000
        self.cpu.push32(float_va)
        self.crt.crt_shim_atof(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), 3.14159, places=5)

    def test_sprintf_and_sscanf(self):
        buf_va = self.mem.heap_alloc(128, 4)
        fmt_va = self.mem.heap_alloc(32, 4)
        str_arg_va = self.mem.heap_alloc(32, 4)
        self.mem.write_bytes(fmt_va, b"Track: %s, Lap: %d\0")
        self.mem.write_bytes(str_arg_va, b"Nevada Highway\0")

        self.cpu.esp = 0x003FF000
        self.cpu.push32(3)            # Lap: 3
        self.cpu.push32(str_arg_va)   # Track: "Nevada Highway"
        self.cpu.push32(fmt_va)       # format
        self.cpu.push32(buf_va)       # buffer
        self.crt.crt_shim_sprintf(self.cpu)

        out_str = self.crt._read_guest_str(buf_va)
        self.assertEqual(out_str, "Track: Nevada Highway, Lap: 3")

        # sscanf
        input_va = self.mem.heap_alloc(32, 4)
        sscanf_fmt_va = self.mem.heap_alloc(16, 4)
        out_lap_va = self.mem.heap_alloc(4, 4)
        out_pos_va = self.mem.heap_alloc(4, 4)
        self.mem.write_bytes(input_va, b"5 1\0")
        self.mem.write_bytes(sscanf_fmt_va, b"%d %d\0")

        self.cpu.esp = 0x003FF000
        self.cpu.push32(out_pos_va)
        self.cpu.push32(out_lap_va)
        self.cpu.push32(sscanf_fmt_va)
        self.cpu.push32(input_va)
        self.crt.crt_shim_sscanf(self.cpu)
        self.assertEqual(self.cpu.eax, 2)
        self.assertEqual(self.mem.read_u32(out_lap_va), 5)
        self.assertEqual(self.mem.read_u32(out_pos_va), 1)

    def test_unary_fpu_intrinsics(self):
        # _CIsin: ST(0) = sin(ST(0))
        self.cpu.fpush(math.pi / 2.0)
        self.crt.crt_shim__CIsin(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), 1.0, places=6)

        # _CIcos
        self.cpu.fpush(0.0)
        self.crt.crt_shim__CIcos(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), 1.0, places=6)

        # _CIsqrt
        self.cpu.fpush(16.0)
        self.crt.crt_shim__CIsqrt(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), 4.0, places=6)

        # _CIexp
        self.cpu.fpush(1.0)
        self.crt.crt_shim__CIexp(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), math.e, places=6)

    def test_binary_fpu_intrinsics(self):
        # _CIpow: caller pushes base, then exponent
        # ST(1) = 2.0 (base), ST(0) = 8.0 (exponent)
        self.cpu.fpush(2.0)
        self.cpu.fpush(8.0)
        self.crt.crt_shim__CIpow(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), 256.0, places=6)

        # _CIatan2: ST(1) = y, ST(0) = x
        self.cpu.fpush(1.0)  # y = 1.0
        self.cpu.fpush(1.0)  # x = 1.0
        self.crt.crt_shim__CIatan2(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), math.pi / 4.0, places=6)

        # _CIfmod: ST(1) = 10.5, ST(0) = 3.0
        self.cpu.fpush(10.5)
        self.cpu.fpush(3.0)
        self.crt.crt_shim__CIfmod(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), 1.5, places=6)

    def test_standard_math_cdecl(self):
        # double sin(double x) via stack
        self.cpu.esp = 0x003FF000
        # push 64-bit double (0.0)
        self.cpu.push32(0)
        self.cpu.push32(0)
        self.crt.crt_shim_sin(self.cpu)
        self.assertAlmostEqual(self.cpu.st_get(0), 0.0, places=6)

        # abs
        self.cpu.esp = 0x003FF000
        self.cpu.push32(0xFFFFFF9C) # -100
        self.crt.crt_shim_abs(self.cpu)
        self.assertEqual(self.cpu.eax, 100)

        # _isnan
        self.cpu.esp = 0x003FF000
        nan_bytes = struct.pack('<d', float('nan'))
        low, high = struct.unpack('<II', nan_bytes)
        self.cpu.push32(high)
        self.cpu.push32(low)
        self.crt.crt_shim__isnan(self.cpu)
        self.assertEqual(self.cpu.eax, 1)

    def test_initterm_execution(self):
        # Mock two static constructors in guest memory
        ctor1_invoked = False
        ctor2_invoked = False

        def ctor1(c: SimulatedCPU):
            nonlocal ctor1_invoked
            ctor1_invoked = True

        def ctor2(c: SimulatedCPU):
            nonlocal ctor2_invoked
            ctor2_invoked = True

        fn1_va = 0x00500000
        fn2_va = 0x00500010
        self.crt.dtab[fn1_va - DISPATCH_TEXT_BASE] = ctor1
        self.crt.dtab[fn2_va - DISPATCH_TEXT_BASE] = ctor2

        tab_va = self.mem.heap_alloc(32, 4)
        self.mem.write_u32(tab_va + 0, fn1_va)
        self.mem.write_u32(tab_va + 4, 0) # null slot
        self.mem.write_u32(tab_va + 8, fn2_va)

        self.cpu.esp = 0x003FF000
        self.cpu.push32(tab_va + 12) # end
        self.cpu.push32(tab_va)      # start
        self.crt.crt_shim__initterm(self.cpu)

        self.assertTrue(ctor1_invoked)
        self.assertTrue(ctor2_invoked)

    def test_setjmp_and_longjmp(self):
        env_va = self.mem.heap_alloc(64, 4)
        self.cpu.esp = 0x003FEE00
        self.cpu.ebp = 0x003FEE10
        self.cpu.ebx = 0x11223344
        self.cpu.esi = 0x55667788
        self.cpu.edi = 0x99AABBCC

        # setjmp
        self.cpu.eip = 0x00410000
        self.cpu.push32(env_va)
        self.crt.crt_shim__setjmp3(self.cpu)
        self.assertEqual(self.cpu.eax, 0)

        # Mutate registers
        self.cpu.ebx = 0
        self.cpu.esi = 0
        self.cpu.edi = 0

        # longjmp with return code 42
        self.cpu.push32(42)
        self.cpu.push32(env_va)
        self.crt.crt_shim_longjmp(self.cpu)
        self.assertEqual(self.cpu.eax, 42)
        self.assertEqual(self.cpu.ebx, 0x11223344)
        self.assertEqual(self.cpu.esi, 0x55667788)
        self.assertEqual(self.cpu.edi, 0x99AABBCC)
        self.assertEqual(self.cpu.eip, 0x00410000)


class TestCrtShimIntegration(unittest.TestCase):
    def setUp(self):
        self.assertTrue(EXE_PATH.exists(), f"Target binary {EXE_PATH} must exist")
        with open(EXE_PATH, 'rb') as f:
            self.exe_bytes = f.read()
        self.mem = GuestMemory()
        self.crt = GuestCRT(self.mem, self.exe_bytes)

    def test_all_156_imports_present_and_continuous(self):
        self.assertEqual(len(self.crt.imports), 156)
        first_va = self.crt.imports[0][0]
        last_va = self.crt.imports[-1][0]
        self.assertEqual(first_va, 0x009671d4)
        self.assertEqual(last_va, 0x00967440)

        # Verify each slot is exactly 4 bytes apart
        for idx in range(1, len(self.crt.imports)):
            prev_va = self.crt.imports[idx - 1][0]
            curr_va = self.crt.imports[idx][0]
            self.assertEqual(curr_va, prev_va + 4)

    def test_iat_binding_into_guest_memory_and_dtab(self):
        self.crt.init_iat()

        # Check metadata initialization
        self.assertEqual(self.mem.read_u32(GUEST_COMMODE_ADDR), 0)
        self.assertEqual(self.mem.read_u32(GUEST_FMODE_ADDR), 0)
        argv_str = self.crt._read_guest_str(GUEST_ARGV_STR_ADDR)
        self.assertEqual(argv_str, "nfs.exe")
        self.assertEqual(self.mem.read_u32(GUEST_ARGV_TAB_ADDR), GUEST_ARGV_STR_ADDR)

        # Check all 156 slots
        for slot_va, sym in self.crt.imports:
            # Memory value at slot_va must equal slot_va
            self.assertEqual(self.mem.read_u32(slot_va), slot_va)
            # Must be present in dtab
            offset = slot_va - DISPATCH_TEXT_BASE
            self.assertIn(offset, self.crt.dtab)

    def test_dispatch_malloc_via_iat(self):
        self.crt.init_iat()
        cpu = SimulatedCPU(self.mem)
        cpu.esp = 0x003FF000
        cpu.push32(512) # size 512

        # Call via IAT slot 0x00967218 (malloc)
        iat_slot_malloc = 0x00967218
        self.crt.dispatch_call(cpu, iat_slot_malloc)
        self.assertGreaterEqual(cpu.eax, 0x02000000)

    def test_dispatch_cisin_via_iat(self):
        self.crt.init_iat()
        cpu = SimulatedCPU(self.mem)
        cpu.fpush(math.pi / 2.0)

        # Call via IAT slot 0x00967280 (_CIsin)
        iat_slot_cisin = 0x00967280
        self.crt.dispatch_call(cpu, iat_slot_cisin)
        self.assertAlmostEqual(cpu.st_get(0), 1.0, places=6)

    def test_generated_c_files_consistency(self):
        root = Path(__file__).resolve().parents[1]
        crt_h = root / "runtime" / "crt.h"
        crt_c = root / "runtime" / "crt.c"
        self.assertTrue(crt_h.exists())
        self.assertTrue(crt_c.exists())

        h_text = crt_h.read_text(encoding='utf-8')
        c_text = crt_c.read_text(encoding='utf-8')

        # Check symbol count mentioned in header
        self.assertIn("Total imported MSVCR80 symbols: 156", h_text)
        self.assertIn("0x009671d4 .. 0x00967440", h_text)

        # Check critical functions in C file
        for sym in ["malloc", "free", "_CIsin", "_CIpow", "_initterm", "_setjmp3", "sprintf"]:
            fn = sanitize_name(sym)
            self.assertIn(f"void {fn}(CPU *c)", c_text)


if __name__ == '__main__':
    unittest.main()