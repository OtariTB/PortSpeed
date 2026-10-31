"""Unit and integration tests for Static C++ Initializer Chain & MSVC Boot Sequence.

Validates _initterm, _initterm_e, atexit / sub_0082851b registration,
LIFO destructor teardown, and all 960 static C++ constructors in nfs.exe.
"""
import json
import unittest
from pathlib import Path

from tools.build_crt_shims import EXE_PATH
from tools.guest_memory import GuestMemory
from tools.guest_crt import GuestCRT, SimulatedCPU, DISPATCH_TEXT_BASE
from tools.guest_win32 import GuestWin32
from tools.guest_initterm import (
    GuestInitterm,
    GUEST_XI_A,
    GUEST_XI_Z,
    GUEST_XC_A,
    GUEST_XC_Z,
    GUEST_SUB_0082851B,
    GUEST_TOTAL_CPP_CTORS,
)


class TestInittermUnit(unittest.TestCase):
    def setUp(self):
        self.mem = GuestMemory()
        self.crt = GuestCRT(self.mem, exe_bytes=None)
        self.crt.init_iat()
        self.w32 = GuestWin32(self.mem, exe_bytes=None)
        self.w32.init_iat()
        self.initterm = GuestInitterm(self.mem, self.crt, self.w32)
        self.initterm.install_hooks()
        self.cpu = SimulatedCPU(self.mem)

    def test_synthetic_c_initializers_success(self):
        invocations = []

        def init1(c: SimulatedCPU):
            invocations.append("init1")
            c.eax = 0

        def init2(c: SimulatedCPU):
            invocations.append("init2")
            c.eax = 0

        fn1 = 0x00510000
        fn2 = 0x00510010
        self.crt.dtab[fn1 - DISPATCH_TEXT_BASE] = init1
        self.crt.dtab[fn2 - DISPATCH_TEXT_BASE] = init2

        tab_va = self.mem.heap_alloc(32, 4)
        self.mem.write_u32(tab_va + 0, 0)
        self.mem.write_u32(tab_va + 4, fn1)
        self.mem.write_u32(tab_va + 8, fn2)

        self.cpu.esp = 0x003FF000
        self.cpu.push32(tab_va + 12)
        self.cpu.push32(tab_va)
        self.crt.crt_shim__initterm_e(self.cpu)

        self.assertEqual(self.cpu.eax, 0)
        self.assertEqual(invocations, ["init1", "init2"])

    def test_synthetic_c_initializers_early_abort(self):
        invocations = []

        def init_fail(c: SimulatedCPU):
            invocations.append("init_fail")
            c.eax = 0x22  # Error code

        def init_never(c: SimulatedCPU):
            invocations.append("init_never")
            c.eax = 0

        fn1 = 0x00510020
        fn2 = 0x00510030
        self.crt.dtab[fn1 - DISPATCH_TEXT_BASE] = init_fail
        self.crt.dtab[fn2 - DISPATCH_TEXT_BASE] = init_never

        tab_va = self.mem.heap_alloc(32, 4)
        self.mem.write_u32(tab_va + 0, fn1)
        self.mem.write_u32(tab_va + 4, fn2)

        self.cpu.esp = 0x003FF000
        self.cpu.push32(tab_va + 8)
        self.cpu.push32(tab_va)
        self.crt.crt_shim__initterm_e(self.cpu)

        self.assertEqual(self.cpu.eax, 0x22)
        self.assertEqual(invocations, ["init_fail"])

    def test_synthetic_cpp_constructors_order_and_null_skipping(self):
        log = []

        def ctor1(c: SimulatedCPU):
            log.append("ctor1")

        def ctor2(c: SimulatedCPU):
            log.append("ctor2")

        def ctor3(c: SimulatedCPU):
            log.append("ctor3")

        va1 = 0x00520000
        va2 = 0x00520010
        va3 = 0x00520020
        self.crt.dtab[va1 - DISPATCH_TEXT_BASE] = ctor1
        self.crt.dtab[va2 - DISPATCH_TEXT_BASE] = ctor2
        self.crt.dtab[va3 - DISPATCH_TEXT_BASE] = ctor3

        tab_va = self.mem.heap_alloc(32, 4)
        self.mem.write_u32(tab_va + 0, va1)
        self.mem.write_u32(tab_va + 4, 0)  # null slot
        self.mem.write_u32(tab_va + 8, va2)
        self.mem.write_u32(tab_va + 12, 0) # null slot
        self.mem.write_u32(tab_va + 16, va3)

        self.cpu.esp = 0x003FF000
        self.cpu.push32(tab_va + 20)
        self.cpu.push32(tab_va)
        self.crt.crt_shim__initterm(self.cpu)

        self.assertEqual(log, ["ctor1", "ctor2", "ctor3"])

    def test_stack_pointer_invariance_across_constructors(self):
        initial_esp = 0x003FF000
        self.cpu.esp = initial_esp

        def buggy_ctor(c: SimulatedCPU):
            # ctor pushes something to stack but fails to pop before returning
            c.push32(0x12345678)

        fn_va = 0x00530000
        self.crt.dtab[fn_va - DISPATCH_TEXT_BASE] = buggy_ctor

        tab_va = self.mem.heap_alloc(16, 4)
        self.mem.write_u32(tab_va + 0, fn_va)

        self.cpu.push32(tab_va + 4)
        self.cpu.push32(tab_va)
        self.crt.crt_shim__initterm(self.cpu)

        # After _initterm loop, esp points back to the arguments
        self.assertEqual(self.cpu.esp, initial_esp - 8)

    def test_hook_sub_0082851b_atexit_registration(self):
        initial_onexit_count = self.crt.get_onexit_count()
        dtor_va = 0x00540000

        # Caller calls sub_0082851b with dtor_va on stack:
        # PUSH32(dtor_va); sub_0082851b(c);
        self.cpu.esp = 0x003FF000
        self.cpu.push32(dtor_va)
        self.crt.dispatch_call(self.cpu, GUEST_SUB_0082851B)

        self.assertEqual(self.cpu.eax, 0)  # atexit returns 0 on success
        self.assertEqual(self.crt.get_onexit_count(), initial_onexit_count + 1)
        self.assertEqual(self.crt.onexit_table[-1], dtor_va)

    def test_lifo_exit_destructors_execution(self):
        destruction_order = []

        def dtor_a(c: SimulatedCPU):
            destruction_order.append("A")

        def dtor_b(c: SimulatedCPU):
            destruction_order.append("B")

        def dtor_c(c: SimulatedCPU):
            destruction_order.append("C")

        va_a = 0x00550000
        va_b = 0x00550010
        va_c = 0x00550020
        self.crt.dtab[va_a - DISPATCH_TEXT_BASE] = dtor_a
        self.crt.dtab[va_b - DISPATCH_TEXT_BASE] = dtor_b
        self.crt.dtab[va_c - DISPATCH_TEXT_BASE] = dtor_c

        # Register in order A, B, C
        self.crt.register_onexit(va_a)
        self.crt.register_onexit(va_b)
        self.crt.register_onexit(va_c)

        # Execute exit destructors
        self.initterm.run_exit_destructors(self.cpu)

        # Must execute in LIFO order: C, B, A
        self.assertEqual(destruction_order, ["C", "B", "A"])
        self.assertEqual(self.crt.get_onexit_count(), 0)


class TestInittermIntegration(unittest.TestCase):
    def setUp(self):
        self.assertTrue(EXE_PATH.exists(), f"Target executable {EXE_PATH} must exist")
        with open(EXE_PATH, 'rb') as f:
            self.exe_bytes = f.read()

        self.mem = GuestMemory()
        self.mem.load_pe_sections(self.exe_bytes)
        self.crt = GuestCRT(self.mem, self.exe_bytes)
        self.crt.init_iat()
        self.w32 = GuestWin32(self.mem, self.exe_bytes)
        self.w32.init_iat()
        self.initterm = GuestInitterm(self.mem, self.crt, self.w32)
        self.initterm.install_hooks()
        self.cpu = SimulatedCPU(self.mem)

    def test_real_prostreet_table_bounds_and_counts(self):
        # 1. C Initializers
        c_inits = self.initterm.get_c_initializers()
        self.assertEqual(len(c_inits), 2)
        self.assertEqual(c_inits, [0x00828b43, 0x00828fee])

        # 2. C++ Static Constructors
        cpp_ctors = self.initterm.get_cpp_constructors()
        self.assertEqual(len(cpp_ctors), GUEST_TOTAL_CPP_CTORS)
        self.assertEqual(len(cpp_ctors), 960)

        # 3. All constructors are unique
        self.assertEqual(len(set(cpp_ctors)), 960)

        # 4. First and last constructor virtual addresses match .rdata
        self.assertEqual(cpp_ctors[0], 0x00828982)
        self.assertEqual(cpp_ctors[-1], 0x009597a0)

    def test_all_constructors_and_helpers_in_catalog(self):
        cat_path = Path(__file__).resolve().parents[1] / "research" / "local" / "phase1" / "catalog.json"
        if not cat_path.exists():
            self.skipTest("catalog.json not present")
        with open(cat_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)

        cat_vas = {fn['address'] for fn in catalog['functions']}

        # Check all 960 constructors
        for ctor_va in self.initterm.get_cpp_constructors():
            self.assertIn(ctor_va, cat_vas, f"Constructor 0x{ctor_va:08x} must be in catalog")

        # Check C initializers
        for c_init in self.initterm.get_c_initializers():
            self.assertIn(c_init, cat_vas, f"C initializer 0x{c_init:08x} must be in catalog")

        # Check sub_0082851b
        self.assertIn(GUEST_SUB_0082851B, cat_vas, "sub_0082851b must be in catalog")

    def test_c_initializers_execution_on_genuine_pe(self):
        # 0x00828b43 checks MZ header in memory at 0x00400000
        # GuestMemory loads PE sections starting at 0x00401000 (.text)
        # Write authentic MZ header at 0x00400000 to satisfy 0x00828b43
        self.mem.write_u16(0x00400000, 0x5a4d)

        # Mock the implementation of the two C initializers in dtab
        def init_dos_check(c: SimulatedCPU):
            mz = self.mem.read_u16(0x00400000)
            c.eax = 0 if mz == 0x5a4d else 1

        def init_cookie(c: SimulatedCPU):
            self.mem.write_u32(0x100f4cc, 0xbb40e64e)
            c.eax = 0

        self.crt.dtab[0x00828b43 - DISPATCH_TEXT_BASE] = init_dos_check
        self.crt.dtab[0x00828fee - DISPATCH_TEXT_BASE] = init_cookie

        res = self.initterm.run_c_initializers(self.cpu)
        self.assertEqual(res, 0)
        self.assertEqual(self.mem.read_u32(0x100f4cc), 0xbb40e64e)

    def test_cpp_constructors_execution_and_destructor_registration(self):
        executed_ctors = []
        registered_dtors = []

        # Wire up mock handlers for all 960 constructors
        for idx, ctor_va in enumerate(self.initterm.get_cpp_constructors()):
            def make_handler(va, i):
                def handler(c: SimulatedCPU):
                    executed_ctors.append(va)
                    # Simulate every 3rd constructor registering an exit destructor
                    if i % 3 == 0:
                        mock_dtor = va + 0x100
                        c.push32(mock_dtor)
                        self.crt.dispatch_call(c, GUEST_SUB_0082851B)
                        c.pop32()
                return handler

            self.crt.dtab[ctor_va - DISPATCH_TEXT_BASE] = make_handler(ctor_va, idx)

        # Run all 960 constructors
        count = self.initterm.run_cpp_constructors(self.cpu)
        self.assertEqual(count, 960)
        self.assertEqual(len(executed_ctors), 960)

        # Exactly 320 destructors registered (960 // 3)
        self.assertEqual(self.crt.get_onexit_count(), 320)

    def test_generated_initterm_c_files_consistency(self):
        root = Path(__file__).resolve().parents[1]
        h_file = root / "runtime" / "initterm.h"
        c_file = root / "runtime" / "initterm.c"
        self.assertTrue(h_file.exists())
        self.assertTrue(c_file.exists())

        h_text = h_file.read_text(encoding='utf-8')
        c_text = c_file.read_text(encoding='utf-8')

        self.assertIn("0x0096a1f8u", h_text)
        self.assertIn("0x0096a204u", h_text)
        self.assertIn("0x00967608u", h_text)
        self.assertIn("0x0096a1f4u", h_text)
        self.assertIn("960u", h_text)
        self.assertIn("0x0082851bu", h_text)

        self.assertIn("void initterm_install_hooks(void)", c_text)
        self.assertIn("int initterm_run_c_initializers(CPU *c)", c_text)
        self.assertIn("uint32_t initterm_run_cpp_constructors(CPU *c)", c_text)
        self.assertIn("void initterm_run_exit_destructors(CPU *c)", c_text)


if __name__ == '__main__':
    unittest.main()

