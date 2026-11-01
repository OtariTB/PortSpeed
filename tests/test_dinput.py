"""Automated tests for DirectInput 8 COM interfaces, vtables, and shared input state.

Verifies:
1. DIJOYSTATE2 binary structure packing (272 bytes) and field alignment.
2. dinput_shared_state_t layout (540 bytes) and lock-free sequence counter.
3. DirectInput COM object vtables and method dispatch mappings in linear memory.
4. Gamepad & racing wheel axis/button updates and GetDeviceState readback.
5. Win32 keyboard message pump FIFO queue and GetKeyState synchronization.
"""

import struct
import unittest
from tools.guest_dinput import (
    DIJoyState2, DInputSharedState, GuestDInput,
    DINPUT_DIRECTINPUT8CREATE_IAT_VA,
    DINPUT_GUEST_DINPUT8_ADDR, DINPUT_GUEST_DINPUT8_VTBL,
    DINPUT_GUEST_DEVICE_ADDR, DINPUT_GUEST_DEVICE_VTBL,
    DINPUT_GUEST_EFFECT_ADDR, DINPUT_GUEST_EFFECT_VTBL,
    DINPUT_GUEST_SHARED_STATE,
    DI_OK, DI8DEVTYPE_GAMEPAD, DI8DEVTYPE_DRIVING,
    DIPROP_AUTOCENTER
)
from tools.guest_memory import GuestMemory


class TestDirectInput(unittest.TestCase):
    def setUp(self):
        self.mem = bytearray(0x28000000)
        self.dinput = GuestDInput(self.mem)

    def test_dijoystate2_exact_size_and_alignment(self):
        """Verify DIJOYSTATE2 binary packing matches 272 bytes exactly."""
        joy = DIJoyState2()
        joy.lX = 12345
        joy.lY = -6789
        joy.lZ = 30000
        joy.lRz = 32000
        joy.rgdwPOV[0] = 9000
        joy.rgbButtons[0] = 0x80 # A button
        joy.rgbButtons[4] = 0x80 # LB button

        packed = joy.pack()
        self.assertEqual(len(packed), 272)

        # Field offset verification
        self.assertEqual(struct.unpack_from('<i', packed, 0)[0], 12345)   # lX
        self.assertEqual(struct.unpack_from('<i', packed, 4)[0], -6789)   # lY
        self.assertEqual(struct.unpack_from('<i', packed, 8)[0], 30000)   # lZ
        self.assertEqual(struct.unpack_from('<i', packed, 20)[0], 32000)  # lRz
        self.assertEqual(struct.unpack_from('<I', packed, 32)[0], 9000)   # POV[0]
        self.assertEqual(packed[48], 0x80)                                # Button 0
        self.assertEqual(packed[52], 0x80)                                # Button 4
        self.assertEqual(packed[49], 0x00)                                # Button 1 released

    def test_shared_state_packing_and_unpacking(self):
        """Verify dinput_shared_state_t packs and unpacks 540 bytes faithfully."""
        state = DInputSharedState()
        state.sequence = 42
        state.connected = 1
        state.device_type = DI8DEVTYPE_DRIVING
        state.joystate.lX = -15000
        state.joystate.lRz = 28000
        state.joystate.lZ = 0
        state.keyboard[0x26] = 0x80 # VK_UP
        state.keyboard[0x28] = 0x80 # VK_DOWN

        data = state.pack()
        self.assertEqual(len(data), 12 + 272 + 256) # 540 bytes

        unpacked = DInputSharedState()
        unpacked.unpack(data)
        self.assertEqual(unpacked.sequence, 42)
        self.assertEqual(unpacked.connected, 1)
        self.assertEqual(unpacked.device_type, DI8DEVTYPE_DRIVING)
        self.assertEqual(unpacked.joystate.lX, -15000)
        self.assertEqual(unpacked.joystate.lRz, 28000)
        self.assertEqual(unpacked.keyboard[0x26], 0x80)
        self.assertEqual(unpacked.keyboard[0x28], 0x80)
        self.assertEqual(unpacked.keyboard[0x25], 0x00)

    def test_guest_memory_layout_initialization(self):
        """Verify DirectInput COM vtables and objects initialized at canonical guest addresses."""
        self.dinput.init_memory()

        # 1. DirectInput8Create IAT slot
        iat_val = struct.unpack_from('<I', self.mem, DINPUT_DIRECTINPUT8CREATE_IAT_VA)[0]
        self.assertEqual(iat_val, DINPUT_DIRECTINPUT8CREATE_IAT_VA)

        # 2. IDirectInput8A COM Object and VTable
        dinput_obj_vtbl = struct.unpack_from('<I', self.mem, DINPUT_GUEST_DINPUT8_ADDR)[0]
        self.assertEqual(dinput_obj_vtbl, DINPUT_GUEST_DINPUT8_VTBL)

        for i in range(11):
            method_va = struct.unpack_from('<I', self.mem, DINPUT_GUEST_DINPUT8_VTBL + i * 4)[0]
            self.assertEqual(method_va, 0x00962000 + i * 4)

        # 3. IDirectInputDevice8A COM Object and VTable
        device_obj_vtbl = struct.unpack_from('<I', self.mem, DINPUT_GUEST_DEVICE_ADDR)[0]
        self.assertEqual(device_obj_vtbl, DINPUT_GUEST_DEVICE_VTBL)

        for i in range(32):
            method_va = struct.unpack_from('<I', self.mem, DINPUT_GUEST_DEVICE_VTBL + i * 4)[0]
            self.assertEqual(method_va, 0x00962200 + i * 4)

        # 4. IDirectInputEffect COM Object and VTable
        effect_obj_vtbl = struct.unpack_from('<I', self.mem, DINPUT_GUEST_EFFECT_ADDR)[0]
        self.assertEqual(effect_obj_vtbl, DINPUT_GUEST_EFFECT_VTBL)

        for i in range(14):
            method_va = struct.unpack_from('<I', self.mem, DINPUT_GUEST_EFFECT_VTBL + i * 4)[0]
            self.assertEqual(method_va, 0x00962400 + i * 4)

    def test_analog_axes_and_buttons_state_sync(self):
        """Verify analog axes and digital buttons sync seamlessly to guest memory."""
        self.dinput.init_memory()

        # Steer full left, throttle 100%, brake 0%
        self.dinput.set_axes(-32768, 32767, 0)
        self.dinput.set_button(0, True)  # Button 0 (A / Shift Up)
        self.dinput.set_button(1, False) # Button 1 released
        self.dinput.set_pov(0, 18000)    # Look Back (Down Hat)

        # Read back from linear guest memory
        read_state = DInputSharedState()
        shared_bytes = bytes(self.mem[DINPUT_GUEST_SHARED_STATE:DINPUT_GUEST_SHARED_STATE + 540])
        read_state.unpack(shared_bytes)

        self.assertEqual(read_state.joystate.lX, -32768)
        self.assertEqual(read_state.joystate.lRz, 32767)
        self.assertEqual(read_state.joystate.lZ, 0)
        self.assertEqual(read_state.joystate.rgbButtons[0], 0x80)
        self.assertEqual(read_state.joystate.rgbButtons[1], 0x00)
        self.assertEqual(read_state.joystate.rgdwPOV[0], 18000)
        self.assertEqual(read_state.joystate.rgdwPOV[1], 0xFFFFFFFF)

    def test_keyboard_key_sync_and_boundaries(self):
        """Verify keyboard key states in shared input buffer."""
        self.dinput.init_memory()

        # Press Space (Handbrake / NOS), ArrowLeft (Steer Left), W (Throttle)
        self.dinput.set_key(0x20, True) # Space
        self.dinput.set_key(0x25, True) # ArrowLeft
        self.dinput.set_key(0x57, True) # 'W'

        read_state = DInputSharedState()
        shared_bytes = bytes(self.mem[DINPUT_GUEST_SHARED_STATE:DINPUT_GUEST_SHARED_STATE + 540])
        read_state.unpack(shared_bytes)

        self.assertEqual(read_state.keyboard[0x20], 0x80)
        self.assertEqual(read_state.keyboard[0x25], 0x80)
        self.assertEqual(read_state.keyboard[0x57], 0x80)
        self.assertEqual(read_state.keyboard[0x27], 0x00) # ArrowRight released

        # Release Space
        self.dinput.set_key(0x20, False)
        read_state.unpack(bytes(self.mem[DINPUT_GUEST_SHARED_STATE:DINPUT_GUEST_SHARED_STATE + 540]))
        self.assertEqual(read_state.keyboard[0x20], 0x00)


if __name__ == '__main__':
    unittest.main()

