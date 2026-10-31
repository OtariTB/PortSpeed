"""Unit tests for Direct3D 9 COM Interface Shim (Substeps 4.1.2 and 4.1.3).

Validates Direct3DCreate9, IDirect3D9 COM vtable (17 methods),
IDirect3DDevice9 COM vtable (119 methods), D3DADAPTER_IDENTIFIER9 1100-byte ABI layout,
heap memory residency, SDK version bounds, COM lifetime, ring buffer draw call
serialization, and strict draw validation.
"""
from __future__ import annotations

from pathlib import Path
import struct
import unittest

from tools.guest_crt import SimulatedCPU
from tools.guest_d3d9 import (
    D3D_OK,
    D3D_SDK_VERSION,
    D3DERR_INVALIDCALL,
    D3DERR_NOTAVAILABLE,
    D3D9_DEVICE_INSTANCE_VA,
    D3D9_DEVICE_METHOD_BASE_VA,
    D3D9_DEVICE_METHODS,
    D3D9_DEVICE_VTABLE_VA,
    D3D9_DIRECT3DCREATE9_IAT_VA,
    D3D9_INSTANCE_VA,
    D3D9_METHOD_BASE_VA,
    D3D9_METHODS,
    D3D9_RING_BUFFER_VA,
    D3D9_VTABLE_VA,
    D3DCommandType,
    E_NOINTERFACE,
    E_POINTER,
    GuestD3D9,
    IID_IDIRECT3D9,
    IID_IDIRECT3DDEVICE9,
    IID_IUNKNOWN,
)
from tools.guest_memory import GuestMemory

WORKSPACE = Path(__file__).resolve().parent.parent


def d3d9_method_va(name: str) -> int:
    return D3D9_METHOD_BASE_VA + D3D9_METHODS.index(name) * 4


def dev_method_va(name: str) -> int:
    return D3D9_DEVICE_METHOD_BASE_VA + D3D9_DEVICE_METHODS.index(name) * 4


class TestD3D9Unit(unittest.TestCase):
    """Unit tests for Direct3D 9 COM interface shim."""

    def setUp(self):
        self.mem = GuestMemory()
        self.cpu = SimulatedCPU(self.mem)
        self.d3d9 = GuestD3D9(self.mem)
        self.d3d9.init_iat()

    def _create_device_helper(self) -> int:
        """Helper to create a valid IDirect3DDevice9 instance."""
        cd_va = d3d9_method_va("CreateDevice")
        pp_params_va = 0x00263000
        out_dev_va = 0x00263100

        self.mem.write_u32(pp_params_va + 0, 1280)
        self.mem.write_u32(pp_params_va + 4, 720)
        self.mem.write_u32(pp_params_va + 8, 22)
        self.mem.write_u32(pp_params_va + 12, 1)
        self.mem.write_u32(pp_params_va + 16, 0)
        self.mem.write_u32(pp_params_va + 20, 0)
        self.mem.write_u32(pp_params_va + 24, 1)
        self.mem.write_u32(pp_params_va + 28, 0x1000)
        self.mem.write_u32(pp_params_va + 32, 1)

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)
        self.mem.write_u32(self.cpu.esp + 8, 1)  # HAL
        self.mem.write_u32(self.cpu.esp + 12, 0x1000)
        self.mem.write_u32(self.cpu.esp + 16, 0x40)
        self.mem.write_u32(self.cpu.esp + 20, pp_params_va)
        self.mem.write_u32(self.cpu.esp + 24, out_dev_va)

        self.d3d9.dtab[cd_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        return self.mem.read_u32(out_dev_va)

    def test_c_source_and_header_consistency(self):
        """Verifies runtime/d3d9.h and runtime/d3d9.c declare all required symbols."""
        h_path = WORKSPACE / "runtime" / "d3d9.h"
        c_path = WORKSPACE / "runtime" / "d3d9.c"

        self.assertTrue(h_path.is_file(), "runtime/d3d9.h must exist")
        self.assertTrue(c_path.is_file(), "runtime/d3d9.c must exist")

        h_code = h_path.read_text(encoding="utf-8")
        c_code = c_path.read_text(encoding="utf-8")

        self.assertIn("0x009675bcu", h_code)
        self.assertIn("D3D9_METHOD_TOTAL_COUNT", h_code)
        self.assertIn("D3D9_DEV_METHOD_TOTAL_COUNT", h_code)
        self.assertIn("d3d9_shim_Direct3DCreate9", h_code)
        self.assertIn("d3d9_init_iat", h_code)

        for name in D3D9_METHODS:
            fn = f"d3d9_shim_{name}"
            self.assertIn(fn, h_code, f"{fn} must be in runtime/d3d9.h")
            self.assertIn(fn, c_code, f"{fn} must be in runtime/d3d9.c")

        for name in D3D9_DEVICE_METHODS:
            fn = f"d3d9_dev_shim_{name}"
            self.assertIn(fn, h_code, f"{fn} must be in runtime/d3d9.h")
            self.assertIn(fn, c_code, f"{fn} must be in runtime/d3d9.c")

    def test_d3dadapter_identifier_abi_layout(self):
        """Verifies D3DADAPTER_IDENTIFIER9 exact 1,100-byte ABI layout and field offsets."""
        ai_va = d3d9_method_va("GetAdapterIdentifier")
        id_buf_va = 0x00260000

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)  # Adapter 0
        self.mem.write_u32(self.cpu.esp + 8, 0)  # Flags
        self.mem.write_u32(self.cpu.esp + 12, id_buf_va)

        # Pre-fill buffer with canary pattern to verify full 1100-byte write
        canary = b"\xAA" * 1200
        self.mem.write_bytes(id_buf_va, canary)

        self.d3d9.dtab[ai_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # 1. Driver string (char[512], offset 0)
        driver_str = self.mem.read_cstring(id_buf_va)
        self.assertEqual(driver_str, "d3d9.dll")

        # 2. Description string (char[512], offset 512)
        desc_str = self.mem.read_cstring(id_buf_va + 512)
        self.assertIn("PortSpeed WebGPU", desc_str)

        # 3. DeviceName string (char[32], offset 1024)
        devname_str = self.mem.read_cstring(id_buf_va + 1024)
        self.assertEqual(devname_str, r"\\.\DISPLAY1")

        # 4. DriverVersion (LARGE_INTEGER, 8 bytes, offset 1056)
        drv_ver_low = self.mem.read_u32(id_buf_va + 1056)
        drv_ver_high = self.mem.read_u32(id_buf_va + 1060)
        self.assertEqual(drv_ver_low, 0)
        self.assertEqual(drv_ver_high, 0x00010000)

        # 5. VendorId (DWORD, offset 1064)
        self.assertEqual(self.mem.read_u32(id_buf_va + 1064), 0x10DE)

        # 6. DeviceId (DWORD, offset 1068)
        self.assertEqual(self.mem.read_u32(id_buf_va + 1068), 0x0402)

        # 7. SubSysId (DWORD, offset 1072)
        self.assertEqual(self.mem.read_u32(id_buf_va + 1072), 0)

        # 8. Revision (DWORD, offset 1076)
        self.assertEqual(self.mem.read_u32(id_buf_va + 1076), 0)

        # 9. DeviceIdentifier GUID (GUID 16 bytes, offset 1080)
        expected_guid = bytes([
            0x3E, 0x1E, 0xB7, 0xD7, 0x42, 0x47, 0xCF, 0x11,
            0x82, 0x6E, 0x01, 0x20, 0x02, 0xC2, 0xCB, 0x35,
        ])
        guid_bytes = self.mem.read_bytes(id_buf_va + 1080, 16)
        self.assertEqual(guid_bytes, expected_guid)

        # 10. WHQLLevel (DWORD, offset 1096)
        self.assertEqual(self.mem.read_u32(id_buf_va + 1096), 0)

        # Verify exact total size: bytes at 1100 must be canary \xAA (untouched)
        self.assertEqual(self.mem.read_bytes(id_buf_va + 1100, 4), b"\xAA\xAA\xAA\xAA")

    def test_direct3dcreate9_sdk_version_check(self):
        """Verifies Direct3DCreate9 accepts 31 and 32, but rejects 0, 30, 33, and 0xFFFFFFFF."""
        for valid_sdk in (31, 32):
            self.cpu.esp = 0x003FE000
            self.mem.write_u32(self.cpu.esp, valid_sdk)
            self.d3d9.dtab[D3D9_DIRECT3DCREATE9_IAT_VA](self.cpu)
            self.assertEqual(self.cpu.eax, D3D9_INSTANCE_VA, f"SDK version {valid_sdk} should succeed")
            self.assertEqual(self.cpu.esp, 0x003FE004)

        for invalid_sdk in (0, 30, 33, 70, 0xFFFFFFFF):
            self.cpu.esp = 0x003FE000
            self.mem.write_u32(self.cpu.esp, invalid_sdk)
            self.d3d9.dtab[D3D9_DIRECT3DCREATE9_IAT_VA](self.cpu)
            self.assertEqual(self.cpu.eax, 0, f"SDK version {invalid_sdk} must be rejected with NULL")
            self.assertEqual(self.cpu.esp, 0x003FE004)

    def test_heap_memory_residency_and_text_integrity(self):
        """Verifies COM vtables and instances reside in heap (0x02001000+) without corrupting .text."""
        self.assertGreaterEqual(D3D9_VTABLE_VA, 0x02000000)
        self.assertGreaterEqual(D3D9_INSTANCE_VA, 0x02000000)
        self.assertGreaterEqual(D3D9_DEVICE_VTABLE_VA, 0x02000000)
        self.assertGreaterEqual(D3D9_DEVICE_INSTANCE_VA, 0x02000000)
        self.assertGreaterEqual(D3D9_RING_BUFFER_VA, 0x02000000)

        # Check authentic executable range (0x00401000..0x00966000) has zero writes
        for va in (0x00401000, 0x0070E1C8, 0x0080AC64, 0x00965FFF):
            self.assertEqual(self.mem.read_u32(va), 0, f"Authentic .text at {hex(va)} must not be overwritten")

    def test_vtable_layout_and_addresses(self):
        """Validates that exactly 17 IDirect3D9 and 119 IDirect3DDevice9 methods are installed."""
        self.assertEqual(len(D3D9_METHODS), 17)
        self.assertEqual(len(D3D9_DEVICE_METHODS), 119)

        # IDirect3D9 vtable
        vtable_ptr = self.mem.read_u32(D3D9_INSTANCE_VA)
        self.assertEqual(vtable_ptr, D3D9_VTABLE_VA)
        for i, name in enumerate(D3D9_METHODS):
            expected_va = D3D9_METHOD_BASE_VA + i * 4
            slot_va = self.mem.read_u32(D3D9_VTABLE_VA + i * 4)
            self.assertEqual(slot_va, expected_va)
            self.assertIn(expected_va, self.d3d9.dtab)

        # IDirect3DDevice9 vtable
        dev_vtable_ptr = self.mem.read_u32(D3D9_DEVICE_INSTANCE_VA)
        self.assertEqual(dev_vtable_ptr, D3D9_DEVICE_VTABLE_VA)
        for i, name in enumerate(D3D9_DEVICE_METHODS):
            expected_va = D3D9_DEVICE_METHOD_BASE_VA + i * 4
            slot_va = self.mem.read_u32(D3D9_DEVICE_VTABLE_VA + i * 4)
            self.assertEqual(slot_va, expected_va)
            self.assertIn(expected_va, self.d3d9.dtab)

    def test_com_addref_and_release(self):
        """Validates COM reference counting on IDirect3D9."""
        addref_va = d3d9_method_va("AddRef")
        release_va = d3d9_method_va("Release")

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.d3d9.dtab[addref_va](self.cpu)
        self.assertEqual(self.cpu.eax, 2)
        self.assertEqual(self.d3d9.ref_count, 2)

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.d3d9.dtab[release_va](self.cpu)
        self.assertEqual(self.cpu.eax, 1)

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.d3d9.dtab[release_va](self.cpu)
        self.assertEqual(self.cpu.eax, 0)
        self.assertFalse(self.d3d9.active)

    def test_com_query_interface(self):
        """Validates QueryInterface for IUnknown, IDirect3D9, unknown GUID, and null pointer."""
        qi_va = d3d9_method_va("QueryInterface")
        riid_va = 0x00250000
        out_ptr_va = 0x00250020

        # Query IID_IUnknown
        self.mem.write_bytes(riid_va, IID_IUNKNOWN)
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, riid_va)
        self.mem.write_u32(self.cpu.esp + 8, out_ptr_va)
        self.d3d9.dtab[qi_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        self.assertEqual(self.mem.read_u32(out_ptr_va), D3D9_INSTANCE_VA)

        # Query IID_IDIRECT3D9
        self.mem.write_bytes(riid_va, IID_IDIRECT3D9)
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, riid_va)
        self.mem.write_u32(self.cpu.esp + 8, out_ptr_va)
        self.d3d9.dtab[qi_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        self.assertEqual(self.mem.read_u32(out_ptr_va), D3D9_INSTANCE_VA)

        # Unknown GUID
        self.mem.write_bytes(riid_va, b"\x22" * 16)
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, riid_va)
        self.mem.write_u32(self.cpu.esp + 8, out_ptr_va)
        self.d3d9.dtab[qi_va](self.cpu)
        self.assertEqual(self.cpu.eax, E_NOINTERFACE)
        self.assertEqual(self.mem.read_u32(out_ptr_va), 0)

        # Null output pointer
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, riid_va)
        self.mem.write_u32(self.cpu.esp + 8, 0)
        self.d3d9.dtab[qi_va](self.cpu)
        self.assertEqual(self.cpu.eax, E_POINTER)

    def test_createdevice_success_and_validation(self):
        """Validates IDirect3D9::CreateDevice creation, parameter validation, and ring buffer init."""
        cd_va = d3d9_method_va("CreateDevice")
        pp_params_va = 0x00263000
        out_dev_va = 0x00263100

        # Presentation parameters (1280x720, windowed)
        self.mem.write_u32(pp_params_va + 0, 1280)  # BackBufferWidth
        self.mem.write_u32(pp_params_va + 4, 720)   # BackBufferHeight
        self.mem.write_u32(pp_params_va + 8, 22)    # BackBufferFormat (D3DFMT_X8R8G8B8)
        self.mem.write_u32(pp_params_va + 12, 1)    # BackBufferCount
        self.mem.write_u32(pp_params_va + 16, 0)    # MultiSampleType
        self.mem.write_u32(pp_params_va + 20, 0)    # MultiSampleQuality
        self.mem.write_u32(pp_params_va + 24, 1)    # SwapEffect (DISCARD)
        self.mem.write_u32(pp_params_va + 28, 0x1000)  # hDeviceWindow
        self.mem.write_u32(pp_params_va + 32, 1)    # Windowed = TRUE
        self.mem.write_u32(pp_params_va + 36, 1)    # EnableAutoDepthStencil
        self.mem.write_u32(pp_params_va + 40, 75)   # AutoDepthStencilFormat (D3DFMT_D24S8)

        # 1. Successful device creation
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)          # Adapter = D3DADAPTER_DEFAULT
        self.mem.write_u32(self.cpu.esp + 8, 1)          # DeviceType = D3DDEVTYPE_HAL
        self.mem.write_u32(self.cpu.esp + 12, 0x1000)    # hFocusWindow
        self.mem.write_u32(self.cpu.esp + 16, 0x40)      # BehaviorFlags (HARDWARE_VERTEXPROCESSING)
        self.mem.write_u32(self.cpu.esp + 20, pp_params_va)
        self.mem.write_u32(self.cpu.esp + 24, out_dev_va)

        self.d3d9.dtab[cd_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        self.assertEqual(self.cpu.esp, 0x003FE01C)  # 28 bytes popped (__stdcall)
        self.assertEqual(self.mem.read_u32(out_dev_va), D3D9_DEVICE_INSTANCE_VA)
        self.assertTrue(self.d3d9.device_active)
        self.assertEqual(self.d3d9.device_ref_count, 1)

        # Ring buffer header should be initialized
        magic = self.mem.read_u32(D3D9_RING_BUFFER_VA)
        self.assertEqual(magic, 0x39443344)  # "D3D9"

        # 2. Parameter error: Adapter != 0
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 1)  # Invalid adapter
        self.mem.write_u32(self.cpu.esp + 8, 1)
        self.mem.write_u32(self.cpu.esp + 12, 0x1000)
        self.mem.write_u32(self.cpu.esp + 16, 0x40)
        self.mem.write_u32(self.cpu.esp + 20, pp_params_va)
        self.mem.write_u32(self.cpu.esp + 24, out_dev_va)

        self.d3d9.dtab[cd_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_INVALIDCALL)

        # 3. Parameter error: Null ppReturnedDeviceInterface
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)
        self.mem.write_u32(self.cpu.esp + 8, 1)
        self.mem.write_u32(self.cpu.esp + 12, 0x1000)
        self.mem.write_u32(self.cpu.esp + 16, 0x40)
        self.mem.write_u32(self.cpu.esp + 20, pp_params_va)
        self.mem.write_u32(self.cpu.esp + 24, 0)  # NULL pointer

        self.d3d9.dtab[cd_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_INVALIDCALL)

        # 4. Parameter error: Invalid DeviceType (e.g. 5)
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)
        self.mem.write_u32(self.cpu.esp + 8, 5)  # Invalid dev type
        self.mem.write_u32(self.cpu.esp + 12, 0x1000)
        self.mem.write_u32(self.cpu.esp + 16, 0x40)
        self.mem.write_u32(self.cpu.esp + 20, pp_params_va)
        self.mem.write_u32(self.cpu.esp + 24, out_dev_va)

        self.d3d9.dtab[cd_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_NOTAVAILABLE)

    def test_device_com_lifetime(self):
        """Validates IDirect3DDevice9 QueryInterface, AddRef, and Release."""
        self._create_device_helper()

        qi_va = dev_method_va("QueryInterface")
        addref_va = dev_method_va("AddRef")
        release_va = dev_method_va("Release")
        riid_va = 0x00251000
        out_ptr_va = 0x00251020

        # 1. AddRef
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.d3d9.dtab[addref_va](self.cpu)
        self.assertEqual(self.cpu.eax, 2)
        self.assertEqual(self.d3d9.device_ref_count, 2)

        # 2. QueryInterface for IDirect3DDevice9
        self.mem.write_bytes(riid_va, IID_IDIRECT3DDEVICE9)
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, riid_va)
        self.mem.write_u32(self.cpu.esp + 8, out_ptr_va)
        self.d3d9.dtab[qi_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        self.assertEqual(self.mem.read_u32(out_ptr_va), D3D9_DEVICE_INSTANCE_VA)
        self.assertEqual(self.d3d9.device_ref_count, 3)

        # 3. Release down to 0
        for expected in (2, 1, 0):
            self.cpu.esp = 0x003FE000
            self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
            self.d3d9.dtab[release_va](self.cpu)
            self.assertEqual(self.cpu.eax, expected)

        self.assertFalse(self.d3d9.device_active)

    def test_device_scene_and_frame_commands(self):
        """Validates BeginScene, EndScene, Clear, and Present ring buffer serialization."""
        self._create_device_helper()

        begin_va = dev_method_va("BeginScene")
        end_va = dev_method_va("EndScene")
        clear_va = dev_method_va("Clear")
        present_va = dev_method_va("Present")

        # 1. Clear
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)          # Count = 0
        self.mem.write_u32(self.cpu.esp + 8, 0)          # pRects = NULL
        self.mem.write_u32(self.cpu.esp + 12, 3)         # Flags (TARGET | ZBUFFER)
        self.mem.write_u32(self.cpu.esp + 16, 0xFF003366) # Color
        self.mem.write_u32(self.cpu.esp + 20, 0x3F800000) # Z = 1.0f
        self.mem.write_u32(self.cpu.esp + 24, 0)         # Stencil = 0
        self.d3d9.dtab[clear_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # 2. BeginScene
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.d3d9.dtab[begin_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # 3. EndScene
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.d3d9.dtab[end_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # 4. Present
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)
        self.mem.write_u32(self.cpu.esp + 8, 0)
        self.mem.write_u32(self.cpu.esp + 12, 0)
        self.mem.write_u32(self.cpu.esp + 16, 0)
        self.d3d9.dtab[present_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # Verify ring buffer commands: CLEAR, BEGIN_SCENE, END_SCENE, PRESENT
        cmds = self.d3d9.ring.read_all_commands()
        cmd_types = [c[0] for c in cmds]
        self.assertIn(D3DCommandType.CLEAR, cmd_types)
        self.assertIn(D3DCommandType.BEGIN_SCENE, cmd_types)
        self.assertIn(D3DCommandType.END_SCENE, cmd_types)
        self.assertIn(D3DCommandType.PRESENT, cmd_types)

        # Header frame index should have incremented
        self.assertGreaterEqual(self.d3d9.ring.hdr.frame_index, 1)

    def test_device_state_and_transforms(self):
        """Validates SetRenderState, GetRenderState, SetViewport, GetViewport, SetTransform."""
        self._create_device_helper()

        srs_va = dev_method_va("SetRenderState")
        grs_va = dev_method_va("GetRenderState")
        svp_va = dev_method_va("SetViewport")
        gvp_va = dev_method_va("GetViewport")
        st_va = dev_method_va("SetTransform")

        # SetRenderState(D3DRS_ZENABLE, 1)
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 7)  # D3DRS_ZENABLE
        self.mem.write_u32(self.cpu.esp + 8, 1)
        self.d3d9.dtab[srs_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # GetRenderState(D3DRS_ZENABLE)
        out_val_va = 0x00264000
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 7)
        self.mem.write_u32(self.cpu.esp + 8, out_val_va)
        self.d3d9.dtab[grs_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        self.assertEqual(self.mem.read_u32(out_val_va), 1)

        # SetViewport
        vp_va = 0x00264100
        self.mem.write_u32(vp_va + 0, 0)     # X
        self.mem.write_u32(vp_va + 4, 0)     # Y
        self.mem.write_u32(vp_va + 8, 1920)  # Width
        self.mem.write_u32(vp_va + 12, 1080) # Height
        self.mem.write_u32(vp_va + 16, 0)    # MinZ = 0.0f
        self.mem.write_u32(vp_va + 20, 0x3F800000) # MaxZ = 1.0f

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, vp_va)
        self.d3d9.dtab[svp_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # GetViewport
        out_vp_va = 0x00264200
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, out_vp_va)
        self.d3d9.dtab[gvp_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        self.assertEqual(self.mem.read_u32(out_vp_va + 8), 1920)
        self.assertEqual(self.mem.read_u32(out_vp_va + 12), 1080)

        # SetTransform (WORLD matrix, 64 bytes)
        mat_va = 0x00264300
        identity_matrix = struct.pack(
            "<16f",
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        )
        self.mem.write_bytes(mat_va, identity_matrix)

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 256) # D3DTS_WORLD
        self.mem.write_u32(self.cpu.esp + 8, mat_va)
        self.d3d9.dtab[st_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

    def test_strict_draw_primitive_validation(self):
        """Verifies DrawPrimitive returns D3DERR_INVALIDCALL when stream 0 is unbound or count is 0."""
        self._create_device_helper()

        dp_va = dev_method_va("DrawPrimitive")
        cvb_va = dev_method_va("CreateVertexBuffer")
        ss_va = dev_method_va("SetStreamSource")

        # 1. Unbound stream 0: must return D3DERR_INVALIDCALL
        self.d3d9.bound_stream0_stride = 0
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 4)   # D3DPT_TRIANGLELIST
        self.mem.write_u32(self.cpu.esp + 8, 0)   # StartVertex
        self.mem.write_u32(self.cpu.esp + 12, 10) # PrimitiveCount = 10
        self.d3d9.dtab[dp_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_INVALIDCALL)

        # 2. Count == 0: must return D3DERR_INVALIDCALL
        self.d3d9.bound_stream0_stride = 32
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 4)
        self.mem.write_u32(self.cpu.esp + 8, 0)
        self.mem.write_u32(self.cpu.esp + 12, 0)  # PrimitiveCount = 0
        self.d3d9.dtab[dp_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_INVALIDCALL)

        # 3. Create VB and bind to stream 0
        out_vb_va = 0x00265000
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 1024)  # Length
        self.mem.write_u32(self.cpu.esp + 8, 0)     # Usage
        self.mem.write_u32(self.cpu.esp + 12, 0)    # FVF
        self.mem.write_u32(self.cpu.esp + 16, 1)    # Pool (DEFAULT)
        self.mem.write_u32(self.cpu.esp + 20, out_vb_va)
        self.mem.write_u32(self.cpu.esp + 24, 0)    # pSharedHandle
        self.d3d9.dtab[cvb_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        vb_handle = self.mem.read_u32(out_vb_va)
        self.assertNotEqual(vb_handle, 0)

        # SetStreamSource(0, vb_handle, 0, 32)
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)          # Stream 0
        self.mem.write_u32(self.cpu.esp + 8, vb_handle)  # pStreamData
        self.mem.write_u32(self.cpu.esp + 12, 0)         # OffsetInBytes
        self.mem.write_u32(self.cpu.esp + 16, 32)        # Stride = 32
        self.d3d9.dtab[ss_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # 4. DrawPrimitive with stream 0 bound and count > 0 succeeds and emits command
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 4)   # D3DPT_TRIANGLELIST
        self.mem.write_u32(self.cpu.esp + 8, 0)   # StartVertex = 0
        self.mem.write_u32(self.cpu.esp + 12, 12) # PrimitiveCount = 12
        self.d3d9.dtab[dp_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        cmds = self.d3d9.ring.read_all_commands()
        draw_cmds = [c for c in cmds if c[0] == D3DCommandType.DRAW_PRIMITIVE]
        self.assertEqual(len(draw_cmds), 1)

    def test_strict_draw_indexed_primitive_validation(self):
        """Verifies DrawIndexedPrimitive returns D3DERR_INVALIDCALL when IB/VB are unbound."""
        self._create_device_helper()

        dip_va = dev_method_va("DrawIndexedPrimitive")
        cib_va = dev_method_va("CreateIndexBuffer")
        si_va = dev_method_va("SetIndices")
        cvb_va = dev_method_va("CreateVertexBuffer")
        ss_va = dev_method_va("SetStreamSource")

        # 1. Unbound stream 0 and unbound IB: fails
        self.d3d9.bound_stream0_stride = 0
        self.d3d9.bound_indices_id = 0
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 4)   # D3DPT_TRIANGLELIST
        self.mem.write_u32(self.cpu.esp + 8, 0)   # BaseVertexIndex
        self.mem.write_u32(self.cpu.esp + 12, 0)  # MinVertexIndex
        self.mem.write_u32(self.cpu.esp + 16, 24) # NumVertices
        self.mem.write_u32(self.cpu.esp + 20, 0)  # StartIndex
        self.mem.write_u32(self.cpu.esp + 24, 12) # PrimitiveCount
        self.d3d9.dtab[dip_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_INVALIDCALL)

        # 2. Bind stream 0 but leave IB unbound: fails
        out_vb_va = 0x00265000
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 1024)
        self.mem.write_u32(self.cpu.esp + 8, 0)
        self.mem.write_u32(self.cpu.esp + 12, 0)
        self.mem.write_u32(self.cpu.esp + 16, 1)
        self.mem.write_u32(self.cpu.esp + 20, out_vb_va)
        self.mem.write_u32(self.cpu.esp + 24, 0)
        self.d3d9.dtab[cvb_va](self.cpu)
        vb_handle = self.mem.read_u32(out_vb_va)

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0)
        self.mem.write_u32(self.cpu.esp + 8, vb_handle)
        self.mem.write_u32(self.cpu.esp + 12, 0)
        self.mem.write_u32(self.cpu.esp + 16, 32)
        self.d3d9.dtab[ss_va](self.cpu)

        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 4)
        self.mem.write_u32(self.cpu.esp + 8, 0)
        self.mem.write_u32(self.cpu.esp + 12, 0)
        self.mem.write_u32(self.cpu.esp + 16, 24)
        self.mem.write_u32(self.cpu.esp + 20, 0)
        self.mem.write_u32(self.cpu.esp + 24, 12)
        self.d3d9.dtab[dip_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_INVALIDCALL)

        # 3. Create IB and bind it
        out_ib_va = 0x00266000
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 512)  # Length
        self.mem.write_u32(self.cpu.esp + 8, 0)    # Usage
        self.mem.write_u32(self.cpu.esp + 12, 101) # Format (D3DFMT_INDEX16)
        self.mem.write_u32(self.cpu.esp + 16, 1)   # Pool (DEFAULT)
        self.mem.write_u32(self.cpu.esp + 20, out_ib_va)
        self.mem.write_u32(self.cpu.esp + 24, 0)
        self.d3d9.dtab[cib_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)
        ib_handle = self.mem.read_u32(out_ib_va)

        # SetIndices(ib_handle)
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, ib_handle)
        self.d3d9.dtab[si_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        # 4. Count == 0: fails
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 4)
        self.mem.write_u32(self.cpu.esp + 8, 0)
        self.mem.write_u32(self.cpu.esp + 12, 0)
        self.mem.write_u32(self.cpu.esp + 16, 24)
        self.mem.write_u32(self.cpu.esp + 20, 0)
        self.mem.write_u32(self.cpu.esp + 24, 0)  # Count = 0
        self.d3d9.dtab[dip_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_INVALIDCALL)

        # 5. Success: both bound and count > 0
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 4)
        self.mem.write_u32(self.cpu.esp + 8, 0)
        self.mem.write_u32(self.cpu.esp + 12, 0)
        self.mem.write_u32(self.cpu.esp + 16, 24)
        self.mem.write_u32(self.cpu.esp + 20, 0)
        self.mem.write_u32(self.cpu.esp + 24, 12) # PrimitiveCount = 12
        self.d3d9.dtab[dip_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3D_OK)

        cmds = self.d3d9.ring.read_all_commands()
        dip_cmds = [c for c in cmds if c[0] == D3DCommandType.DRAW_INDEXED_PRIMITIVE]
        self.assertEqual(len(dip_cmds), 1)

    def test_unsupported_methods_return_failure(self):
        """Verifies unsupported methods return D3DERR_NOTAVAILABLE rather than fake success."""
        # RegisterSoftwareDevice returns D3DERR_NOTAVAILABLE
        reg_va = d3d9_method_va("RegisterSoftwareDevice")
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 0x12345678)
        self.d3d9.dtab[reg_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_NOTAVAILABLE)
        self.assertEqual(self.cpu.esp, 0x003FE008)

        # Device CreateRenderTarget (unsupported) returns D3DERR_NOTAVAILABLE
        crt_va = dev_method_va("CreateRenderTarget")
        self.cpu.esp = 0x003FE000
        self.mem.write_u32(self.cpu.esp, D3D9_DEVICE_INSTANCE_VA)
        self.mem.write_u32(self.cpu.esp + 4, 1280)
        self.mem.write_u32(self.cpu.esp + 8, 720)
        self.mem.write_u32(self.cpu.esp + 12, 22)
        self.mem.write_u32(self.cpu.esp + 16, 0)
        self.mem.write_u32(self.cpu.esp + 20, 0)
        self.mem.write_u32(self.cpu.esp + 24, 1)
        self.mem.write_u32(self.cpu.esp + 28, 0x00267000)
        self.mem.write_u32(self.cpu.esp + 32, 0)
        self.d3d9.dtab[crt_va](self.cpu)
        self.assertEqual(self.cpu.eax, D3DERR_NOTAVAILABLE)


if __name__ == "__main__":
    unittest.main()
