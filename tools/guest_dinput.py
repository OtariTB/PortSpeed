"""DirectInput 8 Python simulation model and guest memory interface.

Provides Python emulation and memory binding for DirectInput8Create,
IDirectInput8A, IDirectInputDevice8A, and IDirectInputEffect COM vtables,
mirroring runtime/dinput.c.
"""

import struct
from typing import Optional, List, Dict, Any

# Protocol Addresses matching runtime/dinput.h
DINPUT_DIRECTINPUT8CREATE_IAT_VA = 0x00967030

DINPUT_GUEST_DINPUT8_ADDR        = 0x02008000
DINPUT_GUEST_DINPUT8_VTBL        = 0x02008100

DINPUT_GUEST_DEVICE_ADDR         = 0x02008300
DINPUT_GUEST_DEVICE_VTBL         = 0x02008400

DINPUT_GUEST_EFFECT_ADDR         = 0x02008600
DINPUT_GUEST_EFFECT_VTBL         = 0x02008700

DINPUT_GUEST_SCRATCH_ADDR        = 0x02009000
DINPUT_GUEST_SHARED_STATE        = 0x0200A000

DINPUT_DINPUT8_METHOD_BASE_VA    = 0x00962000
DINPUT_DEVICE_METHOD_BASE_VA     = 0x00962200
DINPUT_EFFECT_METHOD_BASE_VA     = 0x00962400

# Constants
DI_OK                       = 0x00000000
DI_NOEFFECT                 = 0x00000001
DIERR_INVALIDPARAM          = 0x80070057
DIERR_NOTACQUIRED           = 0x8007000C
DIERR_INPUTLOST             = 0x8007001E

DIRECTINPUT_VERSION         = 0x0800

DI8DEVCLASS_GAMECTRL        = 4

DI8DEVTYPE_JOYSTICK         = 0x14
DI8DEVTYPE_GAMEPAD          = 0x15
DI8DEVTYPE_DRIVING          = 0x16

DIPROP_AUTOCENTER           = 9
DIPROP_RANGE                = 4
DIPROP_DEADZONE             = 5

DIENUM_STOP                 = 0
DIENUM_CONTINUE             = 1


class DIJoyState2:
    """Python representation of DIJOYSTATE2 (272 bytes)."""
    def __init__(self):
        self.lX = 0               # Steering (-32768..32767)
        self.lY = 0
        self.lZ = 0               # Brake / Left Trigger (0..32767 or -32768..32767)
        self.lRx = 0
        self.lRy = 0
        self.lRz = 0              # Throttle / Right Trigger (0..32767 or -32768..32767)
        self.rglSlider = [0, 0]
        self.rgdwPOV = [0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF] # -1 = centered
        self.rgbButtons = bytearray(128)
        self.lVX = self.lVY = self.lVZ = 0
        self.lVRx = self.lVRy = self.lVRz = 0
        self.rglVSlider = [0, 0]
        self.lAX = self.lAY = self.lAZ = 0
        self.lARx = self.lARy = self.lARz = 0
        self.rglASlider = [0, 0]
        self.lFX = self.lFY = self.lFZ = 0
        self.lFRx = self.lFRy = self.lFRz = 0
        self.rglFSlider = [0, 0]

    def pack(self) -> bytes:
        """Packs the DIJOYSTATE2 structure into exactly 272 bytes."""
        hdr = struct.pack(
            '<iiiiii2i4I',
            self.lX, self.lY, self.lZ,
            self.lRx, self.lRy, self.lRz,
            self.rglSlider[0], self.rglSlider[1],
            self.rgdwPOV[0], self.rgdwPOV[1], self.rgdwPOV[2], self.rgdwPOV[3]
        )
        buttons = bytes(self.rgbButtons[:128])
        if len(buttons) < 128:
            buttons = buttons.ljust(128, b'\0')

        tail = struct.pack(
            '<3i3i2i3i3i2i3i3i2i',
            self.lVX, self.lVY, self.lVZ,
            self.lVRx, self.lVRy, self.lVRz,
            self.rglVSlider[0], self.rglVSlider[1],
            self.lAX, self.lAY, self.lAZ,
            self.lARx, self.lARy, self.lARz,
            self.rglASlider[0], self.rglASlider[1],
            self.lFX, self.lFY, self.lFZ,
            self.lFRx, self.lFRy, self.lFRz,
            self.rglFSlider[0], self.rglFSlider[1]
        )
        res = hdr + buttons + tail
        assert len(res) == 272, f"DIJOYSTATE2 packed length must be 272, got {len(res)}"
        return res

    def unpack(self, data: bytes):
        """Unpacks 272 bytes into DIJOYSTATE2 fields."""
        assert len(data) >= 272
        hdr = struct.unpack_from('<iiiiii2i4I', data, 0)
        self.lX, self.lY, self.lZ, self.lRx, self.lRy, self.lRz = hdr[0:6]
        self.rglSlider = [hdr[6], hdr[7]]
        self.rgdwPOV = [hdr[8], hdr[9], hdr[10], hdr[11]]
        self.rgbButtons = bytearray(data[48:48+128])
        tail = struct.unpack_from('<3i3i2i3i3i2i3i3i2i', data, 176)
        self.lVX, self.lVY, self.lVZ = tail[0:3]
        self.lVRx, self.lVRy, self.lVRz = tail[3:6]
        self.rglVSlider = [tail[6], tail[7]]
        self.lAX, self.lAY, self.lAZ = tail[8:11]
        self.lARx, self.lARy, self.lARz = tail[11:14]
        self.rglASlider = [tail[14], tail[15]]
        self.lFX, self.lFY, self.lFZ = tail[16:19]
        self.lFRx, self.lFRy, self.lFRz = tail[19:22]
        self.rglFSlider = [tail[22], tail[23]]


class DInputSharedState:
    """Python representation of dinput_shared_state_t."""
    def __init__(self):
        self.sequence = 1
        self.connected = 1
        self.device_type = DI8DEVTYPE_GAMEPAD
        self.joystate = DIJoyState2()
        self.keyboard = bytearray(256)

    def pack(self) -> bytes:
        """Packs into binary layout matching dinput_shared_state_t."""
        hdr = struct.pack('<Iii', self.sequence, self.connected, self.device_type)
        joy_bytes = self.joystate.pack()
        kbd_bytes = bytes(self.keyboard[:256]).ljust(256, b'\0')
        return hdr + joy_bytes + kbd_bytes

    def unpack(self, data: bytes):
        """Unpacks dinput_shared_state_t."""
        self.sequence, self.connected, self.device_type = struct.unpack_from('<Iii', data, 0)
        self.joystate.unpack(data[12:12+272])
        self.keyboard = bytearray(data[12+272:12+272+256])


class GuestDInput:
    """DirectInput 8 Guest Memory and Interface Manager."""
    def __init__(self, mem: bytearray):
        self.mem = mem
        self.state = DInputSharedState()
        self.acquired = False
        self.dinput_ref_count = 0
        self.device_ref_count = 0
        self.effect_ref_count = 0

    def init_memory(self):
        """Initialize DirectInput COM objects and vtables in guest linear memory."""
        # 1. Bind DirectInput8Create IAT pointer
        struct.pack_into('<I', self.mem, DINPUT_DIRECTINPUT8CREATE_IAT_VA, DINPUT_DIRECTINPUT8CREATE_IAT_VA)

        # 2. Set up IDirectInput8A COM object and vtable (11 methods)
        struct.pack_into('<I', self.mem, DINPUT_GUEST_DINPUT8_ADDR, DINPUT_GUEST_DINPUT8_VTBL)
        for i in range(11):
            struct.pack_into('<I', self.mem, DINPUT_GUEST_DINPUT8_VTBL + i * 4, DINPUT_DINPUT8_METHOD_BASE_VA + i * 4)

        # 3. Set up IDirectInputDevice8A COM object and vtable (32 methods)
        struct.pack_into('<I', self.mem, DINPUT_GUEST_DEVICE_ADDR, DINPUT_GUEST_DEVICE_VTBL)
        for i in range(32):
            struct.pack_into('<I', self.mem, DINPUT_GUEST_DEVICE_VTBL + i * 4, DINPUT_DEVICE_METHOD_BASE_VA + i * 4)

        # 4. Set up IDirectInputEffect COM object and vtable (14 methods)
        struct.pack_into('<I', self.mem, DINPUT_GUEST_EFFECT_ADDR, DINPUT_GUEST_EFFECT_VTBL)
        for i in range(14):
            struct.pack_into('<I', self.mem, DINPUT_GUEST_EFFECT_VTBL + i * 4, DINPUT_EFFECT_METHOD_BASE_VA + i * 4)

        # 5. Sync shared state into guest memory
        self.sync_shared_state()

    def sync_shared_state(self):
        """Writes current shared state to DINPUT_GUEST_SHARED_STATE."""
        data = self.state.pack()
        self.mem[DINPUT_GUEST_SHARED_STATE:DINPUT_GUEST_SHARED_STATE + len(data)] = data

    def read_shared_state(self):
        """Reads shared state from DINPUT_GUEST_SHARED_STATE."""
        data = bytes(self.mem[DINPUT_GUEST_SHARED_STATE:DINPUT_GUEST_SHARED_STATE + 12 + 272 + 256])
        self.state.unpack(data)

    def set_axes(self, steer_lx: int, throttle_rz: int, brake_lz: int):
        self.state.joystate.lX = max(-32768, min(32767, steer_lx))
        self.state.joystate.lRz = max(-32768, min(32767, throttle_rz))
        self.state.joystate.lZ = max(-32768, min(32767, brake_lz))
        self.state.sequence += 1
        self.sync_shared_state()

    def set_button(self, button_idx: int, pressed: bool):
        if 0 <= button_idx < 128:
            self.state.joystate.rgbButtons[button_idx] = 0x80 if pressed else 0x00
            self.state.sequence += 1
            self.sync_shared_state()

    def set_pov(self, hat_idx: int, angle_hundredths: int):
        if 0 <= hat_idx < 4:
            self.state.joystate.rgdwPOV[hat_idx] = angle_hundredths
            self.state.sequence += 1
            self.sync_shared_state()

    def set_key(self, vk: int, pressed: bool):
        if 0 <= vk < 256:
            self.state.keyboard[vk] = 0x80 if pressed else 0x00
            self.state.sequence += 1
            self.sync_shared_state()

