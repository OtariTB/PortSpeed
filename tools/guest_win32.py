"""Python emulation model for NFS ProStreet Win32 Core Emulation Layer.

Mirrors runtime/win32.h and runtime/win32.c, providing unit test verification
for synchronization primitives, QPC timing, TLS allocation, atomic operations,
windowing, and registry queries with strict __stdcall stack discipline.
"""
from __future__ import annotations

import struct
import time
from typing import Callable, Dict, List, Optional, Tuple

from tools.build_win32_shims import (
    ARG_SIZES,
    CORE_DLLS,
    EXE_PATH,
    extract_win32_imports,
    sanitize_name,
)
from tools.guest_crt import SimulatedCPU, DISPATCH_TEXT_BASE, DISPATCH_TEXT_SIZE
from tools.guest_memory import GuestMemory


class GuestWin32:
    """Manages Win32 core shims and IAT registration."""

    def __init__(self, memory: GuestMemory, exe_bytes: Optional[bytes] = None):
        self.mem = memory
        if exe_bytes is None and EXE_PATH.exists():
            with open(EXE_PATH, "rb") as f:
                exe_bytes = f.read()

        self.imports = extract_win32_imports(exe_bytes) if exe_bytes else []
        self.dtab: Dict[int, Callable[[SimulatedCPU], None]] = {}
        self.tls_slots = [0] * 64
        self.tls_bitmap = 0
        self.wnd_proc = 0
        self.win_width = 1280
        self.win_height = 720
        self.msg_queue: List[Tuple[int, int, int, int]] = []
        self.qpc_val = 1000000
        self.tick_count = 50000

    def init_iat(self):
        """Binds all 198 Win32 IAT slots into guest memory and dtab."""
        for dll, slot_va, sym in self.imports:
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
            raise KeyError(f"Unknown Win32 dispatch target: 0x{target_va:08x}")

    def _get_handler(self, sym: str) -> Callable[[SimulatedCPU], None]:
        fn_name = sanitize_name(sym)
        method = getattr(self, fn_name, None)
        if method:
            return method
        pop_bytes = ARG_SIZES.get(sym, 0)
        return lambda c: self._generic_stub(c, pop_bytes)

    def _generic_stub(self, c: SimulatedCPU, pop_bytes: int):
        c.eax = 0
        c.esp = (c.esp + pop_bytes) & 0xFFFFFFFF

    # --------------------------------------------------------------------------
    # Synchronization
    # --------------------------------------------------------------------------
    def win32_shim_InitializeCriticalSection(self, c: SimulatedCPU):
        cs = self.mem.read_u32(c.esp)
        if cs:
            self.mem.write_bytes(cs, b"\0" * 24)
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_EnterCriticalSection(self, c: SimulatedCPU):
        cs = self.mem.read_u32(c.esp)
        if cs:
            rec = self.mem.read_u32(cs + 8)
            self.mem.write_u32(cs + 8, rec + 1)
            self.mem.write_u32(cs + 12, 1000)
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_LeaveCriticalSection(self, c: SimulatedCPU):
        cs = self.mem.read_u32(c.esp)
        if cs:
            rec = self.mem.read_u32(cs + 8)
            if rec > 0:
                self.mem.write_u32(cs + 8, rec - 1)
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_TryEnterCriticalSection(self, c: SimulatedCPU):
        cs = self.mem.read_u32(c.esp)
        if cs:
            rec = self.mem.read_u32(cs + 8)
            self.mem.write_u32(cs + 8, rec + 1)
            self.mem.write_u32(cs + 12, 1000)
        c.eax = 1
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_DeleteCriticalSection(self, c: SimulatedCPU):
        cs = self.mem.read_u32(c.esp)
        if cs:
            self.mem.write_bytes(cs, b"\0" * 24)
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_CreateMutexA(self, c: SimulatedCPU):
        c.eax = 0x1010
        c.esp = (c.esp + 12) & 0xFFFFFFFF

    def win32_shim_CreateMutexW(self, c: SimulatedCPU):
        c.eax = 0x1010
        c.esp = (c.esp + 12) & 0xFFFFFFFF

    def win32_shim_ReleaseMutex(self, c: SimulatedCPU):
        c.eax = 1
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_CreateEventA(self, c: SimulatedCPU):
        c.eax = 0x1020
        c.esp = (c.esp + 16) & 0xFFFFFFFF

    def win32_shim_SetEvent(self, c: SimulatedCPU):
        c.eax = 1
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_ResetEvent(self, c: SimulatedCPU):
        c.eax = 1
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_PulseEvent(self, c: SimulatedCPU):
        c.eax = 1
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_CreateSemaphoreA(self, c: SimulatedCPU):
        c.eax = 0x1030
        c.esp = (c.esp + 16) & 0xFFFFFFFF

    def win32_shim_ReleaseSemaphore(self, c: SimulatedCPU):
        c.eax = 1
        c.esp = (c.esp + 12) & 0xFFFFFFFF

    def win32_shim_WaitForSingleObject(self, c: SimulatedCPU):
        c.eax = 0  # WAIT_OBJECT_0
        c.esp = (c.esp + 8) & 0xFFFFFFFF

    def win32_shim_CloseHandle(self, c: SimulatedCPU):
        c.eax = 1
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_DuplicateHandle(self, c: SimulatedCPU):
        pTarget = self.mem.read_u32(c.esp + 12)
        src = self.mem.read_u32(c.esp + 4)
        if pTarget:
            self.mem.write_u32(pTarget, src)
        c.eax = 1
        c.esp = (c.esp + 28) & 0xFFFFFFFF

    # --------------------------------------------------------------------------
    # Timing & Clocks
    # --------------------------------------------------------------------------
    def win32_shim_QueryPerformanceCounter(self, c: SimulatedCPU):
        pCounter = self.mem.read_u32(c.esp)
        if pCounter:
            self.qpc_val += 16666
            self.mem.write_u64(pCounter, self.qpc_val)
        c.eax = 1
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_QueryPerformanceFrequency(self, c: SimulatedCPU):
        pFreq = self.mem.read_u32(c.esp)
        if pFreq:
            self.mem.write_u64(pFreq, 1000000)
        c.eax = 1
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_GetTickCount(self, c: SimulatedCPU):
        self.tick_count += 16
        c.eax = self.tick_count & 0xFFFFFFFF

    def win32_shim_timeGetTime(self, c: SimulatedCPU):
        self.tick_count += 16
        c.eax = self.tick_count & 0xFFFFFFFF

    def win32_shim_GetSystemTimeAsFileTime(self, c: SimulatedCPU):
        pFT = self.mem.read_u32(c.esp)
        if pFT:
            self.mem.write_u32(pFT + 0, 0x80000000)
            self.mem.write_u32(pFT + 4, 0x01D38000)
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_timeBeginPeriod(self, c: SimulatedCPU):
        c.eax = 0
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_timeEndPeriod(self, c: SimulatedCPU):
        c.eax = 0
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_Sleep(self, c: SimulatedCPU):
        c.eax = 0
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_SleepEx(self, c: SimulatedCPU):
        c.eax = 0
        c.esp = (c.esp + 8) & 0xFFFFFFFF

    # --------------------------------------------------------------------------
    # Thread Local Storage (TLS)
    # --------------------------------------------------------------------------
    def win32_shim_TlsAlloc(self, c: SimulatedCPU):
        for i in range(64):
            if not (self.tls_bitmap & (1 << i)):
                self.tls_bitmap |= (1 << i)
                self.tls_slots[i] = 0
                c.eax = i
                return
        c.eax = 0xFFFFFFFF

    def win32_shim_TlsGetValue(self, c: SimulatedCPU):
        idx = self.mem.read_u32(c.esp)
        c.eax = self.tls_slots[idx] if idx < 64 else 0
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_TlsSetValue(self, c: SimulatedCPU):
        idx = self.mem.read_u32(c.esp)
        val = self.mem.read_u32(c.esp + 4)
        if idx < 64:
            self.tls_slots[idx] = val
        c.eax = 1
        c.esp = (c.esp + 8) & 0xFFFFFFFF

    # --------------------------------------------------------------------------
    # Atomic Operations
    # --------------------------------------------------------------------------
    def win32_shim_InterlockedExchange(self, c: SimulatedCPU):
        pTarget = self.mem.read_u32(c.esp)
        val = self.mem.read_u32(c.esp + 4)
        old = self.mem.read_u32(pTarget)
        self.mem.write_u32(pTarget, val)
        c.eax = old
        c.esp = (c.esp + 8) & 0xFFFFFFFF

    def win32_shim_InterlockedCompareExchange(self, c: SimulatedCPU):
        pDest = self.mem.read_u32(c.esp)
        exch = self.mem.read_u32(c.esp + 4)
        comp = self.mem.read_u32(c.esp + 8)
        old = self.mem.read_u32(pDest)
        if old == comp:
            self.mem.write_u32(pDest, exch)
        c.eax = old
        c.esp = (c.esp + 12) & 0xFFFFFFFF

    def win32_shim_InterlockedDecrement(self, c: SimulatedCPU):
        pAdd = self.mem.read_u32(c.esp)
        val = (self.mem.read_u32(pAdd) - 1) & 0xFFFFFFFF
        self.mem.write_u32(pAdd, val)
        c.eax = val
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_InterlockedExchangeAdd(self, c: SimulatedCPU):
        pAdd = self.mem.read_u32(c.esp)
        val = self.mem.read_u32(c.esp + 4)
        old = self.mem.read_u32(pAdd)
        self.mem.write_u32(pAdd, (old + val) & 0xFFFFFFFF)
        c.eax = old
        c.esp = (c.esp + 8) & 0xFFFFFFFF

    # --------------------------------------------------------------------------
    # Windowing & Messaging (USER32)
    # --------------------------------------------------------------------------
    def win32_shim_RegisterClassExA(self, c: SimulatedCPU):
        lpwcx = self.mem.read_u32(c.esp)
        if lpwcx:
            self.wnd_proc = self.mem.read_u32(lpwcx + 8)
        c.eax = 0xC001
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_CreateWindowExA(self, c: SimulatedCPU):
        c.eax = 0x00010001
        c.esp = (c.esp + 48) & 0xFFFFFFFF

    def win32_shim_GetClientRect(self, c: SimulatedCPU):
        pRect = self.mem.read_u32(c.esp + 4)
        if pRect:
            self.mem.write_u32(pRect + 0, 0)
            self.mem.write_u32(pRect + 4, 0)
            self.mem.write_u32(pRect + 8, self.win_width)
            self.mem.write_u32(pRect + 12, self.win_height)
        c.eax = 1
        c.esp = (c.esp + 8) & 0xFFFFFFFF

    def win32_shim_GetWindowRect(self, c: SimulatedCPU):
        self.win32_shim_GetClientRect(c)

    def win32_shim_AdjustWindowRect(self, c: SimulatedCPU):
        c.eax = 1
        c.esp = (c.esp + 12) & 0xFFFFFFFF

    def win32_shim_DefWindowProcA(self, c: SimulatedCPU):
        c.eax = 0
        c.esp = (c.esp + 16) & 0xFFFFFFFF

    def win32_shim_PeekMessageA(self, c: SimulatedCPU):
        pMsg = self.mem.read_u32(c.esp)
        if self.msg_queue and pMsg:
            hwnd, msg, wp, lp = self.msg_queue.pop(0)
            self.mem.write_u32(pMsg + 0, hwnd)
            self.mem.write_u32(pMsg + 4, msg)
            self.mem.write_u32(pMsg + 8, wp)
            self.mem.write_u32(pMsg + 12, lp)
            self.mem.write_u32(pMsg + 16, int(time.time()))
            self.mem.write_u32(pMsg + 20, 0)
            self.mem.write_u32(pMsg + 24, 0)
            c.eax = 1
        else:
            c.eax = 0
        c.esp = (c.esp + 20) & 0xFFFFFFFF

    def win32_shim_DispatchMessageA(self, c: SimulatedCPU):
        pMsg = self.mem.read_u32(c.esp)
        if self.wnd_proc and pMsg:
            hwnd = self.mem.read_u32(pMsg + 0)
            msg = self.mem.read_u32(pMsg + 4)
            wp = self.mem.read_u32(pMsg + 8)
            lp = self.mem.read_u32(pMsg + 12)
            old_esp = c.esp
            c.push32(lp)
            c.push32(wp)
            c.push32(msg)
            c.push32(hwnd)
            self.dispatch_call(c, self.wnd_proc)
            c.esp = old_esp
        c.eax = 0
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    # --------------------------------------------------------------------------
    # Registry & Security (ADVAPI32)
    # --------------------------------------------------------------------------
    def win32_shim_RegOpenKeyExA(self, c: SimulatedCPU):
        phk = self.mem.read_u32(c.esp + 16)
        if phk:
            self.mem.write_u32(phk, 0x80000001)
        c.eax = 0
        c.esp = (c.esp + 20) & 0xFFFFFFFF

    def win32_shim_RegCreateKeyA(self, c: SimulatedCPU):
        phk = self.mem.read_u32(c.esp + 8)
        if phk:
            self.mem.write_u32(phk, 0x80000001)
        c.eax = 0
        c.esp = (c.esp + 12) & 0xFFFFFFFF

    def win32_shim_RegCloseKey(self, c: SimulatedCPU):
        c.eax = 0
        c.esp = (c.esp + 4) & 0xFFFFFFFF

    def win32_shim_RegQueryValueExA(self, c: SimulatedCPU):
        val_name_va = self.mem.read_u32(c.esp + 4)
        val_name = self.mem.read_cstring(val_name_va)
        pType = self.mem.read_u32(c.esp + 12)
        pData = self.mem.read_u32(c.esp + 16)
        pCb = self.mem.read_u32(c.esp + 20)
        if pType:
            self.mem.write_u32(pType, 1)  # REG_SZ
        if pData and pCb:
            val_bytes = b"English\0" if "Language" in val_name else b".\0"
            self.mem.write_bytes(pData, val_bytes)
            self.mem.write_u32(pCb, len(val_bytes))
        c.eax = 0
        c.esp = (c.esp + 24) & 0xFFFFFFFF
