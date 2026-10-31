"""Unit tests for D3DX9 compiled effect parser across all 34 authentic effects."""

import struct
import unittest
from pathlib import Path
from collections import Counter

from tools.build_win32_shims import EXE_PATH
from tools.inventory_effects import parse_pe_resources
from tools.d3dx9_effect import (
    D3DX9EffectParser,
    MAGIC_FX,
    D3D_END_TOKEN,
)


class TestD3DX9EffectParser(unittest.TestCase):
    """Test suite for validating D3DX9 effect parser against authentic and synthetic data."""

    @classmethod
    def setUpClass(cls):
        """Extract all 34 effect resources from the original executable."""
        cls.exe_bytes = EXE_PATH.read_bytes()
        cls.entries = parse_pe_resources(cls.exe_bytes)
        std_entry = [e for e in cls.entries if e[0] == 'IDI_STANDARD_FX'][0]
        cls.raw_fx = cls.exe_bytes[std_entry[3] : std_entry[3] + std_entry[1]]

    def test_idi_standard_fx_container_header(self):
        """Verify the container magic and header dimensions of IDI_STANDARD_FX."""
        parser = D3DX9EffectParser(self.raw_fx)
        effect = parser.parse()

        self.assertEqual(effect.magic, MAGIC_FX)
        self.assertEqual(effect.technique_count, 2)
        self.assertEqual(len(effect.raw_bytes), 4964)

    def test_idi_standard_fx_parameters(self):
        """Verify that all 17 parameters and semantics are extracted correctly."""
        parser = D3DX9EffectParser(self.raw_fx)
        effect = parser.parse()

        param_names = [p.name for p in effect.parameters]
        self.assertIn("ciMinFilter", param_names)
        self.assertIn("ciMagFilter", param_names)
        self.assertIn("ciMipFilter", param_names)
        self.assertIn("cvVertexPowerBrightness", param_names)
        self.assertIn("kCompressCoeff", param_names)
        self.assertIn("WorldViewProj", param_names)
        self.assertIn("ColorWriteMode", param_names)
        self.assertIn("Cull_Mode", param_names)
        self.assertIn("BaseAddressU", param_names)
        self.assertIn("BaseAddressV", param_names)
        self.assertIn("cvTextureOffset", param_names)
        self.assertIn("DIFFUSE_TEXTURE", param_names)
        self.assertIn("DIFFUSE_SAMPLER", param_names)
        self.assertIn("OPACITY_TEXTURE", param_names)
        self.assertIn("OPACITY_SAMPLER", param_names)

        # Verify semantics on specific parameters
        vpower = [p for p in effect.parameters if p.name == "cvVertexPowerBrightness"][0]
        self.assertEqual(vpower.semantic, "REG_cvVertexPowerBrightness")

        texoff = [p for p in effect.parameters if p.name == "cvTextureOffset"][0]
        self.assertEqual(texoff.semantic, "REG_cvTextureOffset")

    def test_idi_standard_fx_techniques_and_passes(self):
        """Verify technique declarations ('standard' and 'depth') and passes."""
        parser = D3DX9EffectParser(self.raw_fx)
        effect = parser.parse()

        tech_names = [t.name for t in effect.techniques]
        self.assertIn("standard", tech_names)
        self.assertIn("depth", tech_names)

        std_tech = [t for t in effect.techniques if t.name == "standard"][0]
        self.assertEqual(len(std_tech.passes), 1)
        self.assertEqual(std_tech.passes[0].name, "p0")
        self.assertIsNotNone(std_tech.passes[0].vertex_shader)
        self.assertIsNotNone(std_tech.passes[0].pixel_shader)

        depth_tech = [t for t in effect.techniques if t.name == "depth"][0]
        self.assertEqual(len(depth_tech.passes), 1)
        self.assertEqual(depth_tech.passes[0].name, "p0")
        self.assertIsNotNone(depth_tech.passes[0].pixel_shader)

    def test_idi_standard_fx_shader_bytecode(self):
        """Verify precompiled shader bytecodes, CTAB constants, and end tokens."""
        parser = D3DX9EffectParser(self.raw_fx)
        effect = parser.parse()

        # At least 4 authentic shaders must be extracted
        self.assertGreaterEqual(len(effect.shaders), 4)

        # Check Shader 1: Depth PS (ps_2_0, 148 bytes)
        sh1 = [s for s in effect.shaders if s.offset == 0x0840]
        self.assertEqual(len(sh1), 1)
        self.assertEqual(sh1[0].length, 148)
        self.assertEqual(sh1[0].target, "ps_2_0")
        self.assertTrue(sh1[0].creator.startswith("Microsoft (R) D3DX9 Shader Compiler"))
        end_token = struct.unpack_from('<I', sh1[0].bytecode, len(sh1[0].bytecode) - 4)[0]
        self.assertEqual(end_token, D3D_END_TOKEN)

        # Check Shader 2: VS 2.0 (356 bytes, WorldViewProj constant)
        sh2 = [s for s in effect.shaders if s.offset == 0x08ec]
        self.assertEqual(len(sh2), 1)
        self.assertEqual(sh2[0].length, 356)
        self.assertEqual(sh2[0].target, "vs_2_0")
        cnames = [c.name for c in sh2[0].constants]
        self.assertIn("WorldViewProj", cnames)
        wvp = [c for c in sh2[0].constants if c.name == "WorldViewProj"][0]
        self.assertEqual(wvp.register_set, "Float4")
        self.assertEqual(wvp.register_index, 0)
        self.assertEqual(wvp.register_count, 4)

        # Check Shader 3: PS 2.0 (320 bytes, DIFFUSE_SAMPLER and OPACITY_SAMPLER)
        sh3 = [s for s in effect.shaders if s.offset == 0x0a68]
        self.assertEqual(len(sh3), 1)
        self.assertEqual(sh3[0].length, 320)
        self.assertEqual(sh3[0].target, "ps_2_0")
        snames = [c.name for c in sh3[0].constants]
        self.assertIn("DIFFUSE_SAMPLER", snames)
        self.assertIn("OPACITY_SAMPLER", snames)

        # Check Shader 4: Fallback VS 1.1 (460 bytes)
        sh4 = [s for s in effect.shaders if s.offset == 0x0bc0]
        self.assertEqual(len(sh4), 1)
        self.assertEqual(sh4[0].length, 460)
        self.assertEqual(sh4[0].target, "vs_1_1")

    def test_all_34_effects_parsing(self):
        """Verify that all 34 authentic embedded effects parse without errors."""
        self.assertEqual(len(self.entries), 34)

        total_parameters = 0
        total_techniques = 0
        total_shaders = 0

        for name, size, rva, offset in self.entries:
            with self.subTest(effect=name):
                fx_bytes = self.exe_bytes[offset : offset + size]
                parser = D3DX9EffectParser(fx_bytes)
                effect = parser.parse()

                self.assertEqual(effect.magic, MAGIC_FX)
                self.assertGreaterEqual(len(effect.parameters), 10)
                self.assertGreaterEqual(len(effect.techniques), 1)
                self.assertGreaterEqual(len(effect.shaders), 2)

                # Verify each parameter has a valid non-empty string name
                for param in effect.parameters:
                    self.assertTrue(len(param.name) > 0)

                # Verify each shader has valid bytecode terminating in 0x0000FFFF
                for shader in effect.shaders:
                    self.assertGreaterEqual(shader.length, 16)
                    end_tok = struct.unpack_from('<I', shader.bytecode, len(shader.bytecode) - 4)[0]
                    self.assertEqual(end_tok, D3D_END_TOKEN)

                total_parameters += len(effect.parameters)
                total_techniques += len(effect.techniques)
                total_shaders += len(effect.shaders)

        self.assertEqual(total_parameters, 1544)
        self.assertEqual(total_techniques, 230)
        self.assertEqual(total_shaders, 597)

    def test_shader_model_distribution_and_coverage(self):
        """Verify shader model coverage across all 34 effect resources."""
        model_counts = Counter()
        for name, size, rva, offset in self.entries:
            fx_bytes = self.exe_bytes[offset : offset + size]
            parser = D3DX9EffectParser(fx_bytes)
            effect = parser.parse()
            for s in effect.shaders:
                model_counts[s.target] += 1

        # Must find all 6 expected shader targets across the game
        self.assertIn("vs_1_1", model_counts)
        self.assertIn("vs_2_0", model_counts)
        self.assertIn("vs_3_0", model_counts)
        self.assertIn("ps_2_0", model_counts)
        self.assertIn("ps_3_0", model_counts)
        self.assertIn("tx", model_counts)

        self.assertEqual(model_counts["ps_2_0"], 223)
        self.assertEqual(model_counts["vs_2_0"], 199)
        self.assertEqual(model_counts["ps_3_0"], 71)
        self.assertEqual(model_counts["vs_3_0"], 71)
        self.assertEqual(model_counts["vs_1_1"], 27)
        self.assertEqual(model_counts["tx"], 6)

    def test_reject_invalid_magic(self):
        """Verify that an invalid container magic raises ValueError."""
        corrupt = bytearray(self.raw_fx)
        struct.pack_into('<I', corrupt, 0, 0xDEADBEEF)
        parser = D3DX9EffectParser(corrupt)
        with self.assertRaises(ValueError) as ctx:
            parser.parse()
        self.assertIn("Invalid effect magic", str(ctx.exception))

    def test_reject_truncated_header(self):
        """Verify that a truncated effect buffer raises ValueError."""
        truncated = self.raw_fx[:20]
        parser = D3DX9EffectParser(truncated)
        with self.assertRaises(ValueError) as ctx:
            parser.parse()
        self.assertIn("buffer too small", str(ctx.exception))

    def test_reject_out_of_bounds_param_offset(self):
        """Verify that an out-of-bounds parameter table offset raises ValueError."""
        corrupt = bytearray(self.raw_fx)
        struct.pack_into('<I', corrupt, 0x14, 0x100000)  # 1 MB
        parser = D3DX9EffectParser(corrupt)
        with self.assertRaises(ValueError) as ctx:
            parser.parse()
        self.assertIn("out of bounds", str(ctx.exception))

    def test_reject_cyclic_parameter_pointers(self):
        """Verify that cyclic parameter offset loops are safely rejected."""
        corrupt = bytearray(self.raw_fx)
        # Force param 1 (at 0x54) to point back to param 0 (at 0x24)
        # In param 1, next pointer is at offset 0x74 (normally 0x84)
        struct.pack_into('<I', corrupt, 0x74, 0x24)
        parser = D3DX9EffectParser(corrupt)
        with self.assertRaises(ValueError) as ctx:
            parser.parse()
        self.assertIn("Cyclic parameter pointer", str(ctx.exception))

    def test_reject_non_bytes_type(self):
        """Verify that non-bytes arguments raise TypeError."""
        with self.assertRaises(TypeError):
            D3DX9EffectParser("not bytes")  # type: ignore


if __name__ == '__main__':
    unittest.main()
