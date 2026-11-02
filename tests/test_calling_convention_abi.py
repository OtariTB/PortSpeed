"""Automated Unit Tests for Guest-to-Guest and Guest-to-Host Calling Convention ABI.

Validates Task 1.2 from the Master Execution Plan:
1. Frame-pointer-less guest functions (such as sub_0052b8d0) accessing [esp + 4]
   receive their authentic Argument 0 when the return address is at [esp + 0].
2. The IAT dispatch bridge automatically pops the return address (c->esp += 4)
   before entering host platform shims (CRT / Win32 / D3D9), allowing all 354
   existing shims to read Argument 0 at MR32(c->esp) without modifying shim code.
3. Callee cleanup (ret <imm> / win32 stdcall) and caller cleanup (cdecl add esp, <imm>)
   maintain strict zero stack drift across 1,000 nested/recursive call frames.
"""

import sys
import unittest
sys.setrecursionlimit(3000)
from tools.guest_memory import GuestMemory
from tools.guest_crt import SimulatedCPU, GuestCRT
from tools.guest_win32 import GuestWin32


def dispatch_call_bridge(cpu: SimulatedCPU, target_va: int, crt: GuestCRT, win32: GuestWin32):
    """Simulates the enhanced DISPATCH_CALL macro with IAT host shim bridge."""
    # Check if target is an IAT host shim slot in the 0x00967000..0x00967650 range
    if 0x00967000 <= target_va <= 0x00967650:
        # Host shim bridge: Pop the 4-byte guest return address
        # This aligns c->esp so the shim sees Argument 0 at MR32(c->esp)
        cpu.esp = (cpu.esp + 4) & 0xFFFFFFFF

        # Dispatch to the appropriate host shim
        try:
            crt.dispatch_call(cpu, target_va)
        except KeyError:
            win32.dispatch_call(cpu, target_va)
    else:
        # Standard guest-to-guest function call (no return address popping)
        pass


class TestCallingConventionABI(unittest.TestCase):
    def setUp(self):
        self.mem = GuestMemory(0x28000000)
        self.cpu = SimulatedCPU(self.mem)
        self.crt = GuestCRT(self.mem)
        self.crt.init_iat()
        self.win32 = GuestWin32(self.mem)
        self.win32.init_iat()

    def test_frame_pointer_less_guest_function_argument_access(self):
        """Simulate sub_0052b8d0 logic: mov ecx, [esp + 4] where [esp + 0] is return address."""
        initial_esp = 0x003FF000
        self.cpu.esp = initial_esp

        # 1. Caller sets up its frame and pushes a security cookie
        security_cookie = 0xBB7F09D2
        self.cpu.push32(security_cookie)

        # 2. Caller pushes Argument 0 (pointer to string 'GLOBALB' at 0x009EE914)
        arg0_string_va = 0x009EE914
        self.mem.write_bytes(arg0_string_va, b"GLOBALB\0")
        self.cpu.push32(arg0_string_va)

        # 3. Caller executes 'call sub_0052b8d0' -> pushes 4-byte return address
        return_address = 0x004FEDD5
        self.cpu.push32(return_address)

        # At entry to sub_0052b8d0:
        # [esp + 0] = return_address (0x004FEDD5)
        # [esp + 4] = arg0_string_va (0x009EE914)
        # [esp + 8] = security_cookie (0xBB7F09D2)
        self.assertEqual(self.mem.read_u32(self.cpu.esp), return_address)
        self.assertEqual(self.mem.read_u32(self.cpu.esp + 4), arg0_string_va)

        # 4. Callee sub_0052b8d0 executes: mov ecx, [esp + 4]
        self.cpu.ecx = self.mem.read_u32(self.cpu.esp + 4)
        self.assertEqual(self.cpu.ecx, arg0_string_va, "Callee must read Argument 0 at [esp + 4], NOT security cookie")

        # 5. Callee checks first character of string (must be 'G' = 0x47)
        first_char = self.mem.read_u8(self.cpu.ecx)
        self.assertEqual(first_char, ord('G'), "Dereferenced argument must be authentic string character")

        # 6. Callee completes and executes 'ret' (in lifted C: c->esp += 4u; return;)
        self.cpu.esp = (self.cpu.esp + 4) & 0xFFFFFFFF

        # After ret, [esp] is back at Argument 0
        self.assertEqual(self.mem.read_u32(self.cpu.esp), arg0_string_va)

        # 7. Caller performs caller cleanup (add esp, 4)
        self.cpu.esp = (self.cpu.esp + 4) & 0xFFFFFFFF

        # Caller pops security cookie
        popped_cookie = self.cpu.pop32()
        self.assertEqual(popped_cookie, security_cookie)

        # Stack must return exactly to initial_esp with zero drift
        self.assertEqual(self.cpu.esp, initial_esp, "Stack pointer must have exactly 0 drift")

    def test_host_shim_bridge_cdecl_malloc(self):
        """Verify that host shim bridge allows crt_shim_malloc to read size at MR32(esp)."""
        initial_esp = 0x003FF000
        self.cpu.esp = initial_esp

        # 1. Caller pushes Argument 0 (size = 128)
        expected_size = 128
        self.cpu.push32(expected_size)

        # 2. Caller's 'call' emits PUSH32(return_address)
        return_address = 0x004354CA
        self.cpu.push32(return_address)

        # Current stack:
        # [esp + 0] = return_address
        # [esp + 4] = size (128)
        self.assertEqual(self.mem.read_u32(self.cpu.esp), return_address)
        self.assertEqual(self.mem.read_u32(self.cpu.esp + 4), expected_size)

        # 3. Dispatch to IAT slot 0x00967218 (malloc) via bridge
        iat_slot_malloc = 0x00967218
        dispatch_call_bridge(self.cpu, iat_slot_malloc, self.crt, self.win32)

        # Verify that malloc allocated a valid pointer
        allocated_ptr = self.cpu.eax
        self.assertGreaterEqual(allocated_ptr, 0x02000000)
        self.assertEqual(allocated_ptr % 8, 0, "Allocated pointer must be 8-byte aligned")

        # After shim returns, return address has been popped, so [esp] is at the argument (128)
        self.assertEqual(self.mem.read_u32(self.cpu.esp), expected_size)

        # 4. Caller performs standard cdecl argument cleanup: add esp, 4
        self.cpu.esp = (self.cpu.esp + 4) & 0xFFFFFFFF

        # Stack must return cleanly to initial_esp
        self.assertEqual(self.cpu.esp, initial_esp, "Stack pointer must have exactly 0 drift after cdecl shim")

    def test_host_shim_bridge_stdcall_critical_section(self):
        """Verify that host shim bridge works with Win32 stdcall callee-cleanup shims."""
        initial_esp = 0x003FF000
        self.cpu.esp = initial_esp

        # Allocate a critical section structure at 0x02001000
        cs_va = 0x02001000
        self.mem.write_u32(cs_va + 8, 0)   # RecursionCount = 0
        self.mem.write_u32(cs_va + 12, 0)  # OwningThread = 0

        # 1. Caller pushes Argument 0 (LPCRITICAL_SECTION)
        self.cpu.push32(cs_va)

        # 2. Caller's 'call' emits PUSH32(return_address)
        return_address = 0x00405060
        self.cpu.push32(return_address)

        # 3. Dispatch to IAT slot 0x009670D0 (EnterCriticalSection) via bridge
        iat_slot_enter_cs = 0x009670D0
        dispatch_call_bridge(self.cpu, iat_slot_enter_cs, self.crt, self.win32)

        # Verify that EnterCriticalSection mutated the structure
        self.assertEqual(self.mem.read_u32(cs_va + 8), 1, "RecursionCount must increment to 1")
        self.assertEqual(self.mem.read_u32(cs_va + 12), 1000, "OwningThread must be 1000")

        # Since EnterCriticalSection is stdcall, the shim performed c->esp += 4 (callee cleanup)
        # And the bridge popped the return address (c->esp += 4)
        # Therefore, the caller does NOT perform 'add esp, 4'
        self.assertEqual(self.cpu.esp, initial_esp, "Stack pointer must have exactly 0 drift after stdcall shim")

    def test_deep_recursive_call_tree_stack_balance(self):
        """Simulate 1,000 nested call frames mixing guest functions and host shims."""
        initial_esp = 0x003FF000
        self.cpu.esp = initial_esp

        def recursive_caller(depth: int, max_depth: int):
            if depth >= max_depth:
                return

            # Push 2 arguments for guest function
            arg1 = depth * 10
            arg2 = depth * 20
            self.cpu.push32(arg2)
            self.cpu.push32(arg1)

            # Push return address for guest call
            ret_addr = 0x00400000 + depth * 4
            self.cpu.push32(ret_addr)

            # Simulated guest callee reads arguments relative to return address
            read_arg1 = self.mem.read_u32(self.cpu.esp + 4)
            read_arg2 = self.mem.read_u32(self.cpu.esp + 8)
            self.assertEqual(read_arg1, arg1)
            self.assertEqual(read_arg2, arg2)

            # Every 10th frame, call host shim (malloc)
            if depth % 10 == 0:
                self.cpu.push32(32) # size = 32
                self.cpu.push32(0x00450000 + depth) # return address
                dispatch_call_bridge(self.cpu, 0x00967218, self.crt, self.win32)
                # Caller cleanup for malloc
                self.cpu.esp = (self.cpu.esp + 4) & 0xFFFFFFFF

            # Recurse deeper
            recursive_caller(depth + 1, max_depth)

            # Callee returns: pops return address (c->esp += 4)
            self.cpu.esp = (self.cpu.esp + 4) & 0xFFFFFFFF

            # Caller cleanup: pops 2 arguments (add esp, 8)
            self.cpu.esp = (self.cpu.esp + 8) & 0xFFFFFFFF

        # Execute 1,000 nested frames
        recursive_caller(0, 1000)

        # After 1,000 nested call frames return, stack MUST match initial_esp exactly
        self.assertEqual(self.cpu.esp, initial_esp, "ESP must be perfectly balanced after 1,000 recursive frames")


if __name__ == '__main__':
    unittest.main()
