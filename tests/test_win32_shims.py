"""Unit and integration tests for Win32 Core Emulation Layer.

Validates synchronization primitives, QPC timing, thread-local storage,
atomic interlocked operations, window message queue, registry queries,
and 198-slot IAT dispatch binding with strict __stdcall callee stack cleanup.
"""
from pathlib import Path
import unittest

from tools.guest_crt import SimulatedCPU, DISPATCH_TEXT_BASE
from tools.guest_memory import GuestMemory
from tools.guest_win32 import GuestWin32
from tools.build_win32_shims import (
    ARG_SIZES,
    EXE_PATH,
    extract_win32_imports,
    sanitize_name,
)


class TestWin32Unit(unittest.TestCase):
    def setUp(self):
        self.mem = GuestMemory()
        self.w32 = GuestWin32(self.mem, exe_bytes=None)
        self.cpu = SimulatedCPU(self.mem)

    def test_critical_section_lifecycle_and_stack_cleanup(self):
        cs_va = self.mem.heap_alloc(24, 4)
        initial_esp = 0x003FF000

        # 1. InitializeCriticalSection (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(cs_va)
        self.w32.win32_shim_InitializeCriticalSection(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.mem.read_bytes(cs_va, 24), b"\0" * 24)

        # 2. EnterCriticalSection (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(cs_va)
        self.w32.win32_shim_EnterCriticalSection(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.mem.read_u32(cs_va + 8), 1)     # RecursionCount
        self.assertEqual(self.mem.read_u32(cs_va + 12), 1000) # OwningThread

        # 3. Re-entrant EnterCriticalSection
        self.cpu.esp = initial_esp
        self.cpu.push32(cs_va)
        self.w32.win32_shim_EnterCriticalSection(self.cpu)
        self.assertEqual(self.mem.read_u32(cs_va + 8), 2)

        # 4. LeaveCriticalSection (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(cs_va)
        self.w32.win32_shim_LeaveCriticalSection(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.mem.read_u32(cs_va + 8), 1)

        # 5. DeleteCriticalSection (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(cs_va)
        self.w32.win32_shim_DeleteCriticalSection(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.mem.read_bytes(cs_va, 24), b"\0" * 24)

    def test_mutex_event_and_semaphore(self):
        initial_esp = 0x003FF000

        # CreateMutexA (3 args = 12 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(0)  # lpName
        self.cpu.push32(0)  # bInitialOwner
        self.cpu.push32(0)  # lpMutexAttributes
        self.w32.win32_shim_CreateMutexA(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        hMutex = self.cpu.eax
        self.assertGreater(hMutex, 0)

        # ReleaseMutex (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(hMutex)
        self.w32.win32_shim_ReleaseMutex(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 1)

        # CreateEventA (4 args = 16 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(0)  # lpName
        self.cpu.push32(0)  # bInitialState
        self.cpu.push32(0)  # bManualReset
        self.cpu.push32(0)  # lpEventAttributes
        self.w32.win32_shim_CreateEventA(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        hEvent = self.cpu.eax
        self.assertGreater(hEvent, 0)

        # SetEvent & ResetEvent (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(hEvent)
        self.w32.win32_shim_SetEvent(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 1)

        # WaitForSingleObject (2 args = 8 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(100) # dwMilliseconds
        self.cpu.push32(hEvent)
        self.w32.win32_shim_WaitForSingleObject(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 0) # WAIT_OBJECT_0

    def test_tls_allocation_and_retrieval(self):
        initial_esp = 0x003FF000

        # TlsAlloc (0 args)
        self.cpu.esp = initial_esp
        self.w32.win32_shim_TlsAlloc(self.cpu)
        self.assertEqual(self.cpu.eax, 0)

        # TlsSetValue (2 args = 8 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(0xDEADBEEF) # value
        self.cpu.push32(0)          # slot 0
        self.w32.win32_shim_TlsSetValue(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 1)

        # TlsGetValue (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(0) # slot 0
        self.w32.win32_shim_TlsGetValue(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 0xDEADBEEF)

    def test_qpc_and_tick_count(self):
        initial_esp = 0x003FF000
        qpc_buf = self.mem.heap_alloc(8, 8)

        # QueryPerformanceFrequency (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(qpc_buf)
        self.w32.win32_shim_QueryPerformanceFrequency(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.mem.read_u64(qpc_buf), 1000000)

        # QueryPerformanceCounter (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(qpc_buf)
        self.w32.win32_shim_QueryPerformanceCounter(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        qpc1 = self.mem.read_u64(qpc_buf)
        self.assertGreater(qpc1, 1000000)

        # Call again -> monotonic increase
        self.cpu.esp = initial_esp
        self.cpu.push32(qpc_buf)
        self.w32.win32_shim_QueryPerformanceCounter(self.cpu)
        qpc2 = self.mem.read_u64(qpc_buf)
        self.assertGreater(qpc2, qpc1)

        # GetTickCount (0 args)
        self.cpu.esp = initial_esp
        self.w32.win32_shim_GetTickCount(self.cpu)
        self.assertGreater(self.cpu.eax, 0)

    def test_atomic_interlocked_operations(self):
        initial_esp = 0x003FF000
        atom_va = self.mem.heap_alloc(4, 4)
        self.mem.write_u32(atom_va, 50)

        # InterlockedExchange (2 args = 8 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(100)    # new val
        self.cpu.push32(atom_va) # target
        self.w32.win32_shim_InterlockedExchange(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 50) # old
        self.assertEqual(self.mem.read_u32(atom_va), 100)

        # InterlockedCompareExchange (3 args = 12 bytes) - match case
        self.cpu.esp = initial_esp
        self.cpu.push32(100)     # comp
        self.cpu.push32(200)     # exch
        self.cpu.push32(atom_va) # dest
        self.w32.win32_shim_InterlockedCompareExchange(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 100) # old
        self.assertEqual(self.mem.read_u32(atom_va), 200)

        # InterlockedDecrement (1 arg = 4 bytes)
        self.cpu.esp = initial_esp
        self.cpu.push32(atom_va)
        self.w32.win32_shim_InterlockedDecrement(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 199)
        self.assertEqual(self.mem.read_u32(atom_va), 199)

    def test_window_creation_and_messaging(self):
        initial_esp = 0x003FF000

        # CreateWindowExA (12 args = 48 bytes)
        self.cpu.esp = initial_esp
        for _ in range(12):
            self.cpu.push32(0)
        self.w32.win32_shim_CreateWindowExA(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 0x00010001) # HWND

        # GetClientRect (2 args = 8 bytes)
        rect_va = self.mem.heap_alloc(16, 4)
        self.cpu.esp = initial_esp
        self.cpu.push32(rect_va)
        self.cpu.push32(0x00010001)
        self.w32.win32_shim_GetClientRect(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.mem.read_u32(rect_va + 8), 1280)  # right
        self.assertEqual(self.mem.read_u32(rect_va + 12), 720)  # bottom

        # PeekMessageA (5 args = 20 bytes) with empty queue
        msg_va = self.mem.heap_alloc(28, 4)
        self.cpu.esp = initial_esp
        for _ in range(5):
            self.cpu.push32(0)
        self.w32.win32_shim_PeekMessageA(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 0) # No message

        # Push key event and peek again
        self.w32.msg_queue.append((0x00010001, 0x0100, 0x26, 0)) # VK_UP
        self.cpu.esp = initial_esp
        self.cpu.push32(0) # PM_REMOVE
        self.cpu.push32(0)
        self.cpu.push32(0)
        self.cpu.push32(0)
        self.cpu.push32(msg_va)
        self.w32.win32_shim_PeekMessageA(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 1)
        self.assertEqual(self.mem.read_u32(msg_va + 4), 0x0100) # WM_KEYDOWN
        self.assertEqual(self.mem.read_u32(msg_va + 8), 0x26)   # VK_UP

    def test_registry_queries(self):
        initial_esp = 0x003FF000

        # RegOpenKeyExA (5 args = 20 bytes)
        hk_va = self.mem.heap_alloc(4, 4)
        self.cpu.esp = initial_esp
        self.cpu.push32(hk_va)
        self.cpu.push32(0)
        self.cpu.push32(0)
        self.cpu.push32(0)
        self.cpu.push32(0x80000002) # HKEY_LOCAL_MACHINE
        self.w32.win32_shim_RegOpenKeyExA(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 0) # ERROR_SUCCESS
        self.assertEqual(self.mem.read_u32(hk_va), 0x80000001)

        # RegQueryValueExA (6 args = 24 bytes) for Language
        val_name_va = self.mem.heap_alloc(32, 4)
        self.mem.write_bytes(val_name_va, b"Language\0")
        type_va = self.mem.heap_alloc(4, 4)
        data_va = self.mem.heap_alloc(64, 4)
        cb_va = self.mem.heap_alloc(4, 4)
        self.mem.write_u32(cb_va, 64)

        self.cpu.esp = initial_esp
        self.cpu.push32(cb_va)
        self.cpu.push32(data_va)
        self.cpu.push32(type_va)
        self.cpu.push32(0)
        self.cpu.push32(val_name_va)
        self.cpu.push32(0x80000001)
        self.w32.win32_shim_RegQueryValueExA(self.cpu)
        self.assertEqual(self.cpu.esp, initial_esp)
        self.assertEqual(self.cpu.eax, 0)
        self.assertEqual(self.mem.read_cstring(data_va), "English")


class TestWin32Integration(unittest.TestCase):
    def setUp(self):
        self.assertTrue(EXE_PATH.exists(), f"Target binary {EXE_PATH} must exist")
        with open(EXE_PATH, "rb") as f:
            self.exe_bytes = f.read()
        self.mem = GuestMemory()
        self.w32 = GuestWin32(self.mem, self.exe_bytes)

    def test_all_198_win32_imports_present(self):
        self.assertEqual(len(self.w32.imports), 198)

        # Check KERNEL32 imports
        k32 = [sym for dll, va, sym in self.w32.imports if dll == 'KERNEL32.dll']
        self.assertEqual(len(k32), 96)
        self.assertIn('QueryPerformanceCounter', k32)
        self.assertIn('EnterCriticalSection', k32)
        self.assertIn('TlsAlloc', k32)

        # Check USER32 imports
        u32 = [sym for dll, va, sym in self.w32.imports if dll == 'USER32.dll']
        self.assertEqual(len(u32), 40)
        self.assertIn('CreateWindowExA', u32)
        self.assertIn('DispatchMessageA', u32)

        # Check ADVAPI32 imports
        adv = [sym for dll, va, sym in self.w32.imports if dll == 'ADVAPI32.dll']
        self.assertEqual(len(adv), 11)
        self.assertIn('RegOpenKeyExA', adv)

        # Check WS2_32 imports
        ws2 = [sym for dll, va, sym in self.w32.imports if dll == 'WS2_32.dll']
        self.assertEqual(len(ws2), 40)

    def test_iat_binding_into_guest_memory_and_dtab(self):
        self.w32.init_iat()

        for dll, slot_va, sym in self.w32.imports:
            # Slot in guest memory contains slot_va
            self.assertEqual(self.mem.read_u32(slot_va), slot_va)
            # Slot is mapped into dtab
            offset = slot_va - DISPATCH_TEXT_BASE
            self.assertIn(offset, self.w32.dtab)

    def test_dispatch_entercriticalsection_via_iat(self):
        self.w32.init_iat()
        cpu = SimulatedCPU(self.mem)
        cs_va = self.mem.heap_alloc(24, 4)

        # EnterCriticalSection slot = 0x009670d0
        iat_slot_enter_cs = 0x009670d0
        cpu.esp = 0x003FF000
        cpu.push32(cs_va)
        self.w32.dispatch_call(cpu, iat_slot_enter_cs)
        self.assertEqual(cpu.esp, 0x003FF000)
        self.assertEqual(self.mem.read_u32(cs_va + 8), 1)

    def test_dispatch_qpc_via_iat(self):
        self.w32.init_iat()
        cpu = SimulatedCPU(self.mem)
        qpc_buf = self.mem.heap_alloc(8, 8)

        # QueryPerformanceCounter slot = 0x00967178
        iat_slot_qpc = 0x00967178
        cpu.esp = 0x003FF000
        cpu.push32(qpc_buf)
        self.w32.dispatch_call(cpu, iat_slot_qpc)
        self.assertEqual(cpu.esp, 0x003FF000)
        self.assertGreater(self.mem.read_u64(qpc_buf), 1000000)

    def test_generated_win32_c_files_consistency(self):
        root = Path(__file__).resolve().parents[1]
        win32_h = root / "runtime" / "win32.h"
        win32_c = root / "runtime" / "win32.c"
        self.assertTrue(win32_h.exists())
        self.assertTrue(win32_c.exists())

        h_text = win32_h.read_text(encoding="utf-8")
        c_text = win32_c.read_text(encoding="utf-8")

        self.assertIn("Total imported Win32 functions: 198", h_text)
        self.assertIn("void win32_init_iat(void)", h_text)

        # Verify key function implementations exist in C file
        for sym in ["EnterCriticalSection", "QueryPerformanceCounter", "CreateWindowExA", "TlsAlloc", "RegOpenKeyExA"]:
            fn = sanitize_name(sym)
            self.assertIn(f"void {fn}(CPU *c)", c_text)


if __name__ == "__main__":
    unittest.main()
