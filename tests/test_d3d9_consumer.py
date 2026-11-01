"""Tests for Direct3D 9 Command Stream to WebGL2 Integration (Substep 4.1 / Phase 4.3).

Validates the browser-side D3D9 command ring buffer consumer in WebGL2:
1. TypeScript consumer unit tests (header parsing, state machine, wraparound, malformed inputs).
2. End-to-end WebGL2 rendering of the genuine ProStreet graphics initialization command stream
   produced by lifted sub_00705d30 in WebAssembly.
3. Multi-color ARGB unpacking and pixel verification via gl.readPixels in real WebGL2.
4. Sustained ring buffer boundary wraparound rendering in WebGL2 across successive frames.
5. Robust error resilience (corrupt magic, invalid opcodes, truncated payloads, illegal state transitions).
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

WORKSPACE = Path(__file__).resolve().parent.parent


class TestD3D9ConsumerIntegration(unittest.TestCase):
    """Integration test suite for D3D9 command consumer and WebGL2 rendering host."""

    @classmethod
    def setUpClass(cls):
        cls.chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        if not cls.chrome_path.exists():
            cls.chrome_path = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")

        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"

        # Ensure tools/d3d9_consumer.bundle.js exists
        bundle_file = WORKSPACE / "tools" / "d3d9_consumer.bundle.js"
        src_file = WORKSPACE / "web" / "src" / "d3d9_consumer.ts"
        if not bundle_file.exists() or (src_file.exists() and src_file.stat().st_mtime > bundle_file.stat().st_mtime):
            esbuild_bin = WORKSPACE / "web" / "node_modules" / "tsx" / "node_modules" / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
            cmd = (
                [str(esbuild_bin), "web/src/d3d9_consumer.ts", "--bundle", "--format=iife", "--global-name=D3D9", "--outfile=tools/d3d9_consumer.bundle.js"]
                if esbuild_bin.exists()
                else [npx_cmd, "--prefix", "web", "esbuild", "web/src/d3d9_consumer.ts", "--format=iife", "--global-name=D3D9", "--outfile=tools/d3d9_consumer.bundle.js"]
            )
            res_esbuild = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(WORKSPACE),
                check=False,
            )
            assert res_esbuild.returncode == 0, f"esbuild bundling failed:\n{res_esbuild.stderr}"
            res_esbuild = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(WORKSPACE),
                check=False,
            )
            assert res_esbuild.returncode == 0, f"esbuild bundling failed:\n{res_esbuild.stderr}"

    def run_chrome_webgl2(self, script_body: str, timeout: float = 15.0) -> dict:
        """Helper to run a WebGL2 test script in headless Chrome and return parsed JSON."""
        if not self.chrome_path.exists():
            self.skipTest(f"Chrome not found at {self.chrome_path}")

        bundle_js = (WORKSPACE / "tools" / "d3d9_consumer.bundle.js").read_text(encoding="utf-8")
        html = f"""<!DOCTYPE html>
<html><body><pre id="result">WAIT</pre><canvas id="cv" width="640" height="480"></canvas>
<script>
{bundle_js}
</script>
<script>
window.addEventListener('DOMContentLoaded', () => {{
    try {{
        const canvas = document.getElementById('cv');
        const gl = canvas.getContext('webgl2', {{ alpha: true, preserveDrawingBuffer: true }});
        if (!gl) throw new Error('WebGL2 unavailable');
        {script_body}
    }} catch (err) {{
        document.getElementById('result').innerText = JSON.stringify({{
            success: false,
            error: err.toString(),
            stack: err.stack
        }});
    }}
}});
</script></body></html>"""

        test_html = WORKSPACE / "tools" / f"temp_webgl2_test_{os.getpid()}.html"
        test_html.write_text(html, encoding="utf-8")

        try:
            cmd = [
                str(self.chrome_path),
                "--headless=new",
                "--disable-gpu-sandbox",
                "--use-gl=angle",
                "--dump-dom",
                f"file:///{test_html.resolve().as_posix()}",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
            self.assertIsNotNone(match, f"No #result in DOM: {res.stdout[:500]}")
            result = json.loads(match.group(1))
            return result
        finally:
            if test_html.exists():
                test_html.unlink()

    def test_typescript_consumer_unit_tests(self):
        """Runs the standalone TypeScript test suite for D3D9CommandConsumer via tsx."""
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        test_file = "web/tests/d3d9_consumer.test.ts"
        res = subprocess.run(
            [npx_cmd, "--prefix", "web", "tsx", "--test", test_file],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE),
            check=False,
        )
        self.assertEqual(
            res.returncode,
            0,
            f"web/tests/d3d9_consumer.test.ts failed ({res.returncode}):\n{res.stdout}\n{res.stderr}",
        )
        self.assertIn("pass 19", res.stdout)
        self.assertIn("fail 0", res.stdout)

    def test_webgl2_genuine_prostreet_command_stream(self):
        """Feeds genuine lifted sub_00705d30 ring buffer into WebGL2 consumer and verifies rendering."""
        # 1. Execute authentic WebAssembly lifted test to extract genuine ring buffer
        test_script = WORKSPACE / "tests" / "test_d3d9_wasm.mjs"
        res_node = subprocess.run(
            ["node", str(test_script)],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE),
            check=False,
        )
        self.assertEqual(res_node.returncode, 0, f"test_d3d9_wasm.mjs failed:\n{res_node.stderr}")
        stdout = res_node.stdout
        json_start = stdout.find("{")
        self.assertGreaterEqual(json_start, 0)
        report = json.loads(stdout[json_start:])

        raw_b64 = report["ringBuffer"]["rawRingBufferBase64"]
        self.assertTrue(len(raw_b64) > 0, "Must contain raw ring buffer base64")

        # 2. Execute WebGL2 consumer with genuine ring buffer in headless Chrome
        script = f"""
        // Pre-fill canvas with RED (255, 0, 0, 255)
        gl.clearColor(1.0, 0.0, 0.0, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        const initPixels = new Uint8Array(4);
        gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, initPixels);

        // Decode genuine ring buffer binary bytes
        const binStr = atob('{raw_b64}');
        const ringBuf = new ArrayBuffer(64 + 4*1024*1024);
        const u8 = new Uint8Array(ringBuf);
        for (let i = 0; i < binStr.length; i++) {{
            u8[i] = binStr.charCodeAt(i);
        }}

        // Process genuine command stream
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, {{ gl }});
        const cmds = consumer.processCommands();

        // Read pixels at (0, 0), center (320, 240), and corner (639, 479)
        const corner0 = new Uint8Array(4);
        gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, corner0);

        const center = new Uint8Array(4);
        gl.readPixels(320, 240, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, center);

        const corner1 = new Uint8Array(4);
        gl.readPixels(639, 479, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, corner1);

        document.getElementById('result').innerText = JSON.stringify({{
            success: true,
            initPixels: Array.from(initPixels),
            corner0: Array.from(corner0),
            center: Array.from(center),
            corner1: Array.from(corner1),
            cmdTypes: cmds.map(c => c.type),
            presentedFrames: consumer.presentedFrames,
            sceneState: consumer.sceneState,
            lastClear: consumer.lastClear
        }});
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"WebGL2 execution failed: {result.get('error')}")

        # Assertions
        # 1. Initial canvas was RED
        self.assertEqual(result["initPixels"], [255, 0, 0, 255])

        # 2. Executed commands match authentic ProStreet initial frame sequence:
        # 2 = BEGIN_SCENE, 1 = CLEAR, 3 = END_SCENE, 4 = PRESENT
        self.assertEqual(result["cmdTypes"], [2, 1, 3, 4])
        self.assertEqual(result["presentedFrames"], 1)
        self.assertEqual(result["sceneState"], 0)  # IDLE

        # 3. Clear payload matches genuine sub_00705d30 arguments:
        # Flags = 7 (TARGET|ZBUFFER|STENCIL), Color = 0, Z = 1.0f, Stencil = 0
        last_clear = result["lastClear"]
        self.assertEqual(last_clear["flags"], 7)
        self.assertEqual(last_clear["color"], 0)
        self.assertAlmostEqual(last_clear["z"], 1.0, places=4)
        self.assertEqual(last_clear["stencil"], 0)

        # 4. Canvas pixels were cleared to BLACK across the entire viewport
        self.assertEqual(result["corner0"], [0, 0, 0, 0])
        self.assertEqual(result["center"], [0, 0, 0, 0])
        self.assertEqual(result["corner1"], [0, 0, 0, 0])

    def test_webgl2_clear_color_unpacking_and_readback(self):
        """Verifies ARGB unpacking and exact pixel readback for multiple distinct colors in WebGL2."""
        script = """
        const cap = 1024;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        const testColors = [
            // [0xAARRGGBB, [R, G, B, A]]
            [0xFF6495ED, [100, 149, 237, 255]], // Cornflower Blue
            [0xFFFF6600, [255, 102, 0, 255]],   // ProStreet Orange
            [0x80800080, [128, 0, 128, 128]],   // Semi-transparent Purple
            [0xFFFFFFFF, [255, 255, 255, 255]], // Opaque White
            [0xFF123456, [18, 52, 86, 255]],    // Deep Navy
        ];

        const results = [];
        for (const [argb, expectedRgba] of testColors) {
            producer.emitBeginScene();
            producer.emitClear(1, argb, 1.0, 0); // D3DCLEAR_TARGET = 1
            producer.emitEndScene();
            producer.emitPresent(0, 0, 640, 480);

            consumer.processCommands();

            const p = new Uint8Array(4);
            gl.readPixels(100, 100, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, p);
            results.push({
                argb,
                expectedRgba,
                actualRgba: Array.from(p)
            });
        }

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            results: results
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"WebGL2 color unpacking failed: {result.get('error')}")

        for item in result["results"]:
            argb = item["argb"]
            expected = item["expectedRgba"]
            actual = item["actualRgba"]
            self.assertEqual(
                actual,
                expected,
                f"Color mismatch for 0x{argb:08x}: expected {expected}, got {actual}",
            )

    def test_webgl2_ring_buffer_wraparound_rendering(self):
        """Verifies sustained WebGL2 rendering across circular ring buffer wraparound boundaries."""
        script = """
        // 128 bytes capacity forces every 68-byte frame to wrap across the boundary
        const cap = 128;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        const frameResults = [];
        for (let frame = 1; frame <= 10; frame++) {
            const r = (frame * 25) & 0xff;
            const g = (frame * 15) & 0xff;
            const b = (frame * 10) & 0xff;
            const argb = ((0xff << 24) | (r << 16) | (g << 8) | b) >>> 0;

            producer.emitBeginScene();
            producer.emitClear(1, argb, 1.0, 0);
            producer.emitEndScene();
            producer.emitPresent(0, 0, 640, 480);

            const cmds = consumer.processCommands();

            const p = new Uint8Array(4);
            gl.readPixels(50, 50, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, p);

            frameResults.push({
                frame,
                cmdCount: cmds.length,
                pendingBytesAfter: consumer.getPendingBytes(),
                expected: [r, g, b, 255],
                actual: Array.from(p)
            });
        }

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            presentedTotal: consumer.presentedFrames,
            frames: frameResults
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"Wraparound rendering failed: {result.get('error')}")
        self.assertEqual(result["presentedTotal"], 10)

        for f in result["frames"]:
            self.assertEqual(f["cmdCount"], 4)
            self.assertEqual(f["pendingBytesAfter"], 0)
            self.assertEqual(
                f["actual"],
                f["expected"],
                f"Frame {f['frame']} pixel corrupted across wraparound: expected {f['expected']}, got {f['actual']}",
            )

    def test_webgl2_consumer_error_resilience(self):
        """Verifies that malformed packets and invalid state transitions throw descriptive errors."""
        script = """
        const cap = 512;
        const ringBuf = new ArrayBuffer(64 + cap);
        const view = new DataView(ringBuf);
        const errors = [];

        // 1. Corrupt magic
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        view.setUint32(0, 0x12345678, true);
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.validateRingHeader();
        } catch (e) {
            errors.push({ test: 'corrupt_magic', msg: e.message });
        }

        // 2. Unsupported version
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        view.setUint32(4, 99, true);
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.validateRingHeader();
        } catch (e) {
            errors.push({ test: 'bad_version', msg: e.message });
        }

        // 3. Double BeginScene
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p1 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p1.emitBeginScene();
        p1.emitBeginScene();
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'double_begin_scene', msg: e.message });
        }

        // 4. EndScene without BeginScene
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p2 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p2.emitEndScene();
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'end_scene_idle', msg: e.message });
        }

        // 5. Present while in scene
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p3 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p3.emitBeginScene();
        p3.emitPresent(0, 0, 640, 480);
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'present_in_scene', msg: e.message });
        }

        // 6. Unknown opcode 88
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p4 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p4.emitRawPacket(88, 0, null);
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'unknown_opcode', msg: e.message });
        }

        // 7. Truncated CLEAR payload
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p5 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p5.emitRawPacket(1, 0, new Uint8Array(4)); // CLEAR requires 20 bytes
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'truncated_clear', msg: e.message });
        }

        // 8. Unsupported render state: FOGENABLE (28)
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p6 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p6.emitSetRenderState(28, 1);
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'unsupported_state', msg: e.message });
        }

        // 9. Unsupported ZENABLE value (D3DZB_USEW = 2)
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p7 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p7.emitSetRenderState(7, 2);
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'unsupported_zenable', msg: e.message });
        }

        // 10. Unsupported COLORWRITEENABLE (> 15)
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p8 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p8.emitSetRenderState(168, 16);
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'unsupported_colorwrite', msg: e.message });
        }

        // 11. Invalid viewport depth range (minZ > maxZ)
        D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const p9 = new D3D9.D3D9CommandProducer(ringBuf, 0);
        p9.emitSetViewport(0, 0, 640, 480, 0.9, 0.1);
        try {
            const c = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });
            c.processCommands();
        } catch (e) {
            errors.push({ test: 'invalid_viewport_depth', msg: e.message });
        }

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            errors: errors
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"Error resilience check failed: {result.get('error')}")

        errors_by_test = {e["test"]: e["msg"] for e in result["errors"]}
        self.assertIn("corrupt_magic", errors_by_test)
        self.assertIn("Invalid ring buffer magic", errors_by_test["corrupt_magic"])

        self.assertIn("bad_version", errors_by_test)
        self.assertIn("Unsupported ring buffer version", errors_by_test["bad_version"])

        self.assertIn("double_begin_scene", errors_by_test)
        self.assertIn("already IN_SCENE", errors_by_test["double_begin_scene"])

        self.assertIn("end_scene_idle", errors_by_test)
        self.assertIn("while IDLE", errors_by_test["end_scene_idle"])

        self.assertIn("present_in_scene", errors_by_test)
        self.assertIn("while IN_SCENE", errors_by_test["present_in_scene"])

        self.assertIn("unknown_opcode", errors_by_test)
        self.assertIn("Invalid command opcode", errors_by_test["unknown_opcode"])

        self.assertIn("truncated_clear", errors_by_test)
        self.assertIn("Truncated CLEAR payload", errors_by_test["truncated_clear"])

        self.assertIn("unsupported_state", errors_by_test)
        self.assertIn("Unsupported render state", errors_by_test["unsupported_state"])

        self.assertIn("unsupported_zenable", errors_by_test)
        self.assertIn("Unsupported ZENABLE value", errors_by_test["unsupported_zenable"])

        self.assertIn("unsupported_colorwrite", errors_by_test)
        self.assertIn("Unsupported COLORWRITEENABLE value", errors_by_test["unsupported_colorwrite"])

        self.assertIn("invalid_viewport_depth", errors_by_test)
        self.assertIn("Invalid viewport depth range", errors_by_test["invalid_viewport_depth"])

    def test_webgl2_set_viewport_and_scissor_clear(self):
        """Verifies D3D9 to WebGL2 viewport conversion and viewport-bounded clear behavior."""
        script = """
        const cap = 1024;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // 1. Initial clear: entire canvas 640x480 to RED (255, 0, 0, 255)
        producer.emitBeginScene();
        producer.emitClear(1, 0xFFFF0000, 1.0, 0); // RED
        producer.emitEndScene();
        producer.emitPresent(0, 0, 640, 480);
        consumer.processCommands();

        // 2. Set sub-viewport: D3D9 (x=100, y=50, w=200, h=150, minZ=0.1, maxZ=0.9)
        // Canvas height is 480. WebGL coordinates:
        // glX = 100, glY = 480 - (50 + 150) = 280, glWidth = 200, glHeight = 150.
        producer.emitSetViewport(100, 50, 200, 150, 0.1, 0.9);

        // 3. Clear viewport to BLUE (0xFF0000FF = 0, 0, 255, 255)
        producer.emitBeginScene();
        producer.emitClear(1, 0xFF0000FF, 1.0, 0); // BLUE
        producer.emitEndScene();
        producer.emitPresent(0, 0, 640, 480);
        consumer.processCommands();

        // Query WebGL viewport and depth range
        const glVp = Array.from(gl.getParameter(gl.VIEWPORT));
        const glDepthRange = Array.from(gl.getParameter(gl.DEPTH_RANGE));

        // Read pixels:
        // (a) Inside viewport at WebGL (150, 300) -> must be BLUE (0, 0, 255, 255)
        const insidePixel = new Uint8Array(4);
        gl.readPixels(150, 300, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, insidePixel);

        // (b) Outside viewport at WebGL (20, 20) -> must STILL BE RED (255, 0, 0, 255)
        const outsidePixel1 = new Uint8Array(4);
        gl.readPixels(20, 20, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, outsidePixel1);

        // (c) Outside viewport at WebGL (500, 400) -> must STILL BE RED (255, 0, 0, 255)
        const outsidePixel2 = new Uint8Array(4);
        gl.readPixels(500, 400, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, outsidePixel2);

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            glVp: glVp,
            glDepthRange: glDepthRange,
            insidePixel: Array.from(insidePixel),
            outsidePixel1: Array.from(outsidePixel1),
            outsidePixel2: Array.from(outsidePixel2)
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"Viewport WebGL2 test failed: {result.get('error')}")

        # WebGL Viewport: [100, 280, 200, 150]
        self.assertEqual(result["glVp"], [100, 280, 200, 150])
        self.assertAlmostEqual(result["glDepthRange"][0], 0.1, places=2)
        self.assertAlmostEqual(result["glDepthRange"][1], 0.9, places=2)

        # Pixel assertions
        self.assertEqual(result["insidePixel"], [0, 0, 255, 255], "Pixel inside viewport must be cleared to BLUE")
        self.assertEqual(result["outsidePixel1"], [255, 0, 0, 255], "Pixel outside viewport must remain RED")
        self.assertEqual(result["outsidePixel2"], [255, 0, 0, 255], "Pixel outside viewport must remain RED")

    def test_webgl2_color_write_mask_clear_rendering(self):
        """Verifies that D3D9 Clear writes all channels regardless of COLORWRITEENABLE, and mask remains active for geometry."""
        script = """
        const cap = 1024;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // Helper to render a diagnostic fullscreen quad with a given color
        function drawDiagnosticQuad(r, g, b, a) {
            const vs = gl.createShader(gl.VERTEX_SHADER);
            gl.shaderSource(vs, `#version 300 es
                void main() {
                    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
                    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
                }`);
            gl.compileShader(vs);

            const fs = gl.createShader(gl.FRAGMENT_SHADER);
            gl.shaderSource(fs, `#version 300 es
                precision mediump float;
                uniform vec4 uColor;
                out vec4 fragColor;
                void main() { fragColor = uColor; }`);
            gl.compileShader(fs);

            const prog = gl.createProgram();
            gl.attachShader(prog, vs);
            gl.attachShader(prog, fs);
            gl.linkProgram(prog);
            gl.useProgram(prog);

            const uLoc = gl.getUniformLocation(prog, 'uColor');
            gl.uniform4f(uLoc, r, g, b, a);

            const vao = gl.createVertexArray();
            gl.bindVertexArray(vao);
            gl.disable(gl.DEPTH_TEST);
            gl.disable(gl.CULL_FACE);
            gl.disable(gl.BLEND);
            gl.drawArrays(gl.TRIANGLES, 0, 3);

            gl.deleteProgram(prog);
            gl.deleteShader(vs);
            gl.deleteShader(fs);
            gl.deleteVertexArray(vao);
        }

        // 1. Initial clear to WHITE (255, 255, 255, 255)
        producer.emitSetRenderState(168, 15); // COLORWRITEENABLE = 0xF
        producer.emitClear(1, 0xFFFFFFFF, 1.0, 0);
        consumer.processCommands();

        // 2. Set COLORWRITEENABLE = RED | BLUE (1 | 4 = 5). Green and Alpha masked.
        producer.emitSetRenderState(168, 5);
        consumer.processCommands();
        const maskBeforeClear = Array.from(gl.getParameter(gl.COLOR_WRITEMASK));

        // 3. Direct3D 9 Clear: Clear must write ALL channels regardless of COLORWRITEENABLE
        // Clear to BLACK (0, 0, 0, 0).
        producer.emitClear(1, 0x00000000, 1.0, 0);
        consumer.processCommands();

        // Read pixels immediately after Clear: ALL channels must be cleared to 0 (0, 0, 0, 0)
        const clearPixels = new Uint8Array(4);
        gl.readPixels(50, 50, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, clearPixels);

        // Verify that the color-write mask is restored to [true, false, true, false] after Clear
        const maskAfterClear = Array.from(gl.getParameter(gl.COLOR_WRITEMASK));

        // 4. Subsequent geometry rendering: draw WHITE (1, 1, 1, 1)
        // Since COLORWRITEENABLE = RED | BLUE is active, only Red and Blue are written.
        // Green and Alpha remain 0 from the clear! Result must be (255, 0, 255, 0).
        drawDiagnosticQuad(1.0, 1.0, 1.0, 1.0);
        const geometryPixels = new Uint8Array(4);
        gl.readPixels(50, 50, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, geometryPixels);

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            maskBeforeClear: maskBeforeClear,
            clearPixels: Array.from(clearPixels),
            maskAfterClear: maskAfterClear,
            geometryPixels: Array.from(geometryPixels)
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"Color mask test failed: {result.get('error')}")

        # Mask before clear is [true, false, true, false]
        self.assertEqual(result["maskBeforeClear"], [True, False, True, False])

        # Clear ignores D3DRS_COLORWRITEENABLE and clears ALL 4 channels to 0
        self.assertEqual(result["clearPixels"], [0, 0, 0, 0], "D3D9 Clear must write all channels regardless of COLORWRITEENABLE")

        # Mask after clear is restored to [true, false, true, false]
        self.assertEqual(result["maskAfterClear"], [True, False, True, False], "Color mask must be restored after Clear")

        # Subsequent geometry draw only writes Red and Blue; Green and Alpha stay 0 -> [255, 0, 255, 0]
        self.assertEqual(
            result["geometryPixels"],
            [255, 0, 255, 0],
            "Subsequent geometry rendering must strictly respect the active COLORWRITEENABLE mask",
        )

    def test_webgl2_depth_mask_clear_override(self):
        """Verifies that D3D9 Clear clears depth even when ZWRITEENABLE is FALSE, and restores the mask."""
        script = """
        const cap = 1024;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // 1. Clear color to BLACK and depth to 0.0
        producer.emitClear(3, 0x00000000, 0.0, 0); // TARGET | ZBUFFER, z=0.0
        consumer.processCommands();

        // 2. Set ZWRITEENABLE = FALSE (0)
        producer.emitSetRenderState(14, 0);
        consumer.processCommands();
        const maskBefore = gl.getParameter(gl.DEPTH_WRITEMASK);

        // 3. Clear depth to 0.8: Direct3D 9 must write depth to 0.8 even though ZWRITEENABLE=0!
        producer.emitClear(2, 0x00000000, 0.8, 0); // ZBUFFER, z=0.8
        consumer.processCommands();

        // Verify that depthMask was restored to false after clear
        const maskAfter = gl.getParameter(gl.DEPTH_WRITEMASK);

        // 4. Verify depth was indeed cleared to 0.8 by testing with depthFunc(LESS):
        // Render a quad at NDC z=0.0 -> window depth 0.5.
        // If clear succeeded, 0.5 < 0.8 passes depth test and writes GREEN (0, 255, 0, 255).
        // If clear had been blocked by depthMask(false), depth would be 0.0, and 0.5 < 0.0 would fail!
        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `#version 300 es
            void main() {
                vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
                gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0); // z_clip = 0.0 -> z_win = 0.5
            }`);
        gl.compileShader(vs);

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `#version 300 es
            precision mediump float;
            out vec4 fragColor;
            void main() { fragColor = vec4(0.0, 1.0, 0.0, 1.0); }`);
        gl.compileShader(fs);

        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        gl.useProgram(prog);

        const vao = gl.createVertexArray();
        gl.bindVertexArray(vao);
        gl.disable(gl.CULL_FACE);
        gl.enable(gl.DEPTH_TEST);
        gl.depthFunc(gl.LESS);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        const testPixels = new Uint8Array(4);
        gl.readPixels(50, 50, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, testPixels);

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            maskBefore: maskBefore,
            maskAfter: maskAfter,
            testPixels: Array.from(testPixels)
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"Depth mask clear override failed: {result.get('error')}")

        self.assertFalse(result["maskBefore"], "Depth write mask should be false before clear")
        self.assertFalse(result["maskAfter"], "Depth write mask should be restored to false after clear")
        self.assertEqual(
            result["testPixels"],
            [0, 255, 0, 255],
            "Depth clear must update depth buffer to 0.8 even when ZWRITEENABLE is false, allowing z=0.5 to pass depth test",
        )

    def test_webgl2_depth_test_and_cull_render_states(self):
        """Verifies ZENABLE, ZWRITEENABLE, ZFUNC, and CULLMODE states on real WebGL2 context."""
        script = """
        const cap = 2048;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // Verify initial defaults
        const initDepthTest = gl.getParameter(gl.DEPTH_TEST);
        const initDepthMask = gl.getParameter(gl.DEPTH_WRITEMASK);
        const initDepthFunc = gl.getParameter(gl.DEPTH_FUNC);
        const initCullFace = gl.getParameter(gl.CULL_FACE);
        const initCullMode = gl.getParameter(gl.CULL_FACE_MODE);

        // 1. Disable ZENABLE
        producer.emitSetRenderState(7, 0); // ZENABLE = FALSE
        consumer.processCommands();
        const depthTestOff = gl.getParameter(gl.DEPTH_TEST);

        // 2. Enable ZENABLE, disable ZWRITEENABLE
        producer.emitSetRenderState(7, 1); // ZENABLE = TRUE
        producer.emitSetRenderState(14, 0); // ZWRITEENABLE = FALSE
        consumer.processCommands();
        const depthTestOn = gl.getParameter(gl.DEPTH_TEST);
        const depthMaskOff = gl.getParameter(gl.DEPTH_WRITEMASK);

        // 3. Test all 8 ZFUNC comparison functions
        // 1: NEVER, 2: LESS, 3: EQUAL, 4: LEQUAL, 5: GREATER, 6: NOTEQUAL, 7: GEQUAL, 8: ALWAYS
        const depthFuncResults = [];
        for (let func = 1; func <= 8; func++) {
            producer.emitSetRenderState(23, func);
            consumer.processCommands();
            depthFuncResults.push(gl.getParameter(gl.DEPTH_FUNC));
        }

        // 4. Test CULLMODE: 1=NONE, 2=CW, 3=CCW
        producer.emitSetRenderState(22, 1); // CULLMODE_NONE
        consumer.processCommands();
        const cullNone = gl.getParameter(gl.CULL_FACE);

        producer.emitSetRenderState(22, 2); // CULLMODE_CW
        consumer.processCommands();
        const cullCwEnabled = gl.getParameter(gl.CULL_FACE);
        const cullCwMode = gl.getParameter(gl.CULL_FACE_MODE);

        producer.emitSetRenderState(22, 3); // CULLMODE_CCW
        consumer.processCommands();
        const cullCcwEnabled = gl.getParameter(gl.CULL_FACE);
        const cullCcwMode = gl.getParameter(gl.CULL_FACE_MODE);

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            initDepthTest: initDepthTest,
            initDepthMask: initDepthMask,
            initDepthFunc: initDepthFunc,
            initCullFace: initCullFace,
            initCullMode: initCullMode,
            depthTestOff: depthTestOff,
            depthTestOn: depthTestOn,
            depthMaskOff: depthMaskOff,
            depthFuncResults: depthFuncResults,
            cullNone: cullNone,
            cullCwEnabled: cullCwEnabled,
            cullCwMode: cullCwMode,
            cullCcwEnabled: cullCcwEnabled,
            cullCcwMode: cullCcwMode
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"Depth and Cull test failed: {result.get('error')}")

        # Defaults
        self.assertTrue(result["initDepthTest"])
        self.assertTrue(result["initDepthMask"])
        self.assertEqual(result["initDepthFunc"], 0x0203)  # gl.LEQUAL
        self.assertTrue(result["initCullFace"])
        self.assertEqual(result["initCullMode"], 0x0405)  # gl.BACK (culls CCW)

        # Toggles
        self.assertFalse(result["depthTestOff"])
        self.assertTrue(result["depthTestOn"])
        self.assertFalse(result["depthMaskOff"])

        # Comparison funcs 1..8: NEVER (0x200), LESS (0x201), EQUAL (0x202), LEQUAL (0x203),
        # GREATER (0x204), NOTEQUAL (0x205), GEQUAL (0x206), ALWAYS (0x207)
        expected_funcs = [0x0200, 0x0201, 0x0202, 0x0203, 0x0204, 0x0205, 0x0206, 0x0207]
        self.assertEqual(result["depthFuncResults"], expected_funcs)

        # Culling
        self.assertFalse(result["cullNone"])
        self.assertTrue(result["cullCwEnabled"])
        self.assertEqual(result["cullCwMode"], 0x0404)  # gl.FRONT (culls CW)
        self.assertTrue(result["cullCcwEnabled"])
        self.assertEqual(result["cullCcwMode"], 0x0405)  # gl.BACK (culls CCW)

    def test_webgl2_alpha_blend_render_states(self):
        """Verifies ALPHABLENDENABLE, SRCBLEND, and DESTBLEND states on real WebGL2 context."""
        script = """
        const cap = 1024;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // Verify initial default: blend disabled, ONE, ZERO
        const initBlend = gl.getParameter(gl.BLEND);
        const initSrc = gl.getParameter(gl.BLEND_SRC_RGB);
        const initDst = gl.getParameter(gl.BLEND_DST_RGB);

        // 1. Enable blend
        producer.emitSetRenderState(27, 1); // ALPHABLENDENABLE = TRUE
        consumer.processCommands();
        const blendOn = gl.getParameter(gl.BLEND);

        // 2. Set standard alpha blend: SRCALPHA (5) + INVSRCALPHA (6)
        producer.emitSetRenderState(19, 5); // SRCBLEND = SRCALPHA
        producer.emitSetRenderState(20, 6); // DESTBLEND = INVSRCALPHA
        consumer.processCommands();
        const srcAlpha = gl.getParameter(gl.BLEND_SRC_RGB);
        const invSrcAlpha = gl.getParameter(gl.BLEND_DST_RGB);

        // 3. Set additive blend: ONE (2) + ONE (2)
        producer.emitSetRenderState(19, 2);
        producer.emitSetRenderState(20, 2);
        consumer.processCommands();
        const addSrc = gl.getParameter(gl.BLEND_SRC_RGB);
        const addDst = gl.getParameter(gl.BLEND_DST_RGB);

        // 4. Disable blend
        producer.emitSetRenderState(27, 0); // ALPHABLENDENABLE = FALSE
        consumer.processCommands();
        const blendOff = gl.getParameter(gl.BLEND);

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            initBlend: initBlend,
            initSrc: initSrc,
            initDst: initDst,
            blendOn: blendOn,
            srcAlpha: srcAlpha,
            invSrcAlpha: invSrcAlpha,
            addSrc: addSrc,
            addDst: addDst,
            blendOff: blendOff
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"Alpha blend test failed: {result.get('error')}")

        # Defaults
        self.assertFalse(result["initBlend"])
        self.assertEqual(result["initSrc"], 1)  # gl.ONE
        self.assertEqual(result["initDst"], 0)  # gl.ZERO

        # Alpha blend (SRCALPHA=0x0302, INVSRCALPHA=0x0303)
        self.assertTrue(result["blendOn"])
        self.assertEqual(result["srcAlpha"], 0x0302)
        self.assertEqual(result["invSrcAlpha"], 0x0303)

        # Additive blend (ONE=1, ONE=1)
        self.assertEqual(result["addSrc"], 1)
        self.assertEqual(result["addDst"], 1)

        # Disable blend
        self.assertFalse(result["blendOff"])

    def test_webgl2_vertex_buffer_lifecycle_and_gpu_readback(self):
        """Verifies WebGLBuffer allocation, bufferSubData upload, GPU getBufferSubData readback, and deletion."""
        script = """
        const cap = 4096;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // 1. Create static VB (id=1, 64 bytes) and dynamic VB (id=2, 128 bytes, D3DUSAGE_DYNAMIC=0x200)
        producer.emitCreateVertexBuffer(1, 64, 0x08, 0x142, 1);
        producer.emitCreateVertexBuffer(2, 128, 0x208, 0, 0);
        consumer.processCommands();

        const vb1 = consumer.getVertexBuffer(1);
        const vb2 = consumer.getVertexBuffer(2);

        gl.bindBuffer(gl.ARRAY_BUFFER, vb1.glBuffer);
        const vb1Size = gl.getBufferParameter(gl.ARRAY_BUFFER, gl.BUFFER_SIZE);
        const vb1Usage = gl.getBufferParameter(gl.ARRAY_BUFFER, gl.BUFFER_USAGE);
        const vb1ValidBefore = gl.isBuffer(vb1.glBuffer);

        gl.bindBuffer(gl.ARRAY_BUFFER, vb2.glBuffer);
        const vb2Size = gl.getBufferParameter(gl.ARRAY_BUFFER, gl.BUFFER_SIZE);
        const vb2Usage = gl.getBufferParameter(gl.ARRAY_BUFFER, gl.BUFFER_USAGE);

        // 2. Upload initial 8 floats (32 bytes) to vb1 at offset 0
        const initialFloats = new Float32Array([1.5, -2.5, 3.25, 4.0, 10.0, 20.0, 30.0, 40.0]);
        producer.emitUpdateVertexBuffer(1, 0, initialFloats);

        // 3. Partial sub-data update: overwrite floats[4..7] at byte offset 16 and append floats[8..11] at byte offset 32
        const patchFloats = new Float32Array([55.0, 66.0, 77.0, 88.0, 100.5, 200.5, 300.5, 400.5]);
        producer.emitUpdateVertexBuffer(1, 16, patchFloats);
        consumer.processCommands();

        // 4. Read back directly from GPU VRAM via WebGL2 gl.getBufferSubData
        gl.bindBuffer(gl.ARRAY_BUFFER, vb1.glBuffer);
        const gpuReadback = new Float32Array(12);
        gl.getBufferSubData(gl.ARRAY_BUFFER, 0, gpuReadback);

        // 5. Bind stream 0 to vb1 (offset=16, stride=16), then destroy vb1
        producer.emitSetStreamSource(0, 1, 16, 16);
        consumer.processCommands();
        const streamBeforeDestroy = { ...consumer.getStreamSource(0) };

        const rawGlBuf1 = vb1.glBuffer;
        producer.emitDestroyVertexBuffer(1);
        consumer.processCommands();

        const vb1ValidAfter = gl.isBuffer(rawGlBuf1);
        const streamAfterDestroy = { ...consumer.getStreamSource(0) };

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            vb1Size,
            vb1Usage,
            vb1ValidBefore,
            vb1ValidAfter,
            vb2Size,
            vb2Usage,
            gpuReadback: Array.from(gpuReadback),
            streamBeforeDestroy,
            streamAfterDestroy
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"WebGL2 VB lifecycle failed: {result.get('error')}")

        self.assertEqual(result["vb1Size"], 64)
        self.assertEqual(result["vb1Usage"], 0x88E4)  # gl.STATIC_DRAW
        self.assertTrue(result["vb1ValidBefore"])
        self.assertFalse(result["vb1ValidAfter"])

        self.assertEqual(result["vb2Size"], 128)
        self.assertEqual(result["vb2Usage"], 0x88E8)  # gl.DYNAMIC_DRAW

        expected_floats = [
            1.5, -2.5, 3.25, 4.0,
            55.0, 66.0, 77.0, 88.0,
            100.5, 200.5, 300.5, 400.5,
        ]
        self.assertEqual(result["gpuReadback"], expected_floats)

        self.assertEqual(result["streamBeforeDestroy"]["bufferId"], 1)
        self.assertEqual(result["streamBeforeDestroy"]["offset"], 16)
        self.assertEqual(result["streamBeforeDestroy"]["stride"], 16)

        self.assertEqual(result["streamAfterDestroy"]["bufferId"], 0)
        self.assertEqual(result["streamAfterDestroy"]["offset"], 0)
        self.assertEqual(result["streamAfterDestroy"]["stride"], 0)

    def test_webgl2_vertex_buffer_stream_binding_diagnostic_draw(self):
        """Verifies rendering geometry from a D3D9 vertex buffer bound via SET_STREAM_SOURCE with non-zero offset and stride."""
        script = """
        const cap = 4096;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // Allocate a 256-byte dynamic vertex buffer (bufferId = 3)
        producer.emitCreateVertexBuffer(3, 256, 0x200, 0, 0);

        // Interleaved vertex format: [x, y, r, g, b, a] = 6 floats = 24 bytes stride.
        // Upload 3 vertices (fullscreen triangle colored pure ProStreet Green: 0.0, 1.0, 0.25, 1.0)
        // at a non-zero byte offset of 48 bytes inside vertex buffer 3.
        const triVerts = new Float32Array([
            -1.0, -1.0,   0.0, 1.0, 0.0, 1.0,
             3.0, -1.0,   0.0, 1.0, 0.0, 1.0,
            -1.0,  3.0,   0.0, 1.0, 0.0, 1.0,
        ]);
        producer.emitUpdateVertexBuffer(3, 48, triVerts);

        // Bind vertex buffer 3 to stream 0 with byte offset = 48, stride = 24
        producer.emitSetStreamSource(0, 3, 48, 24);
        consumer.processCommands();

        // Clear screen to black
        producer.emitBeginScene();
        producer.emitClear(1, 0xFF000000, 1.0, 0);
        producer.emitEndScene();
        consumer.processCommands();

        // Execute diagnostic draw using the bound stream 0 state from consumer
        const stream0 = consumer.getStreamSource(0);
        const vbEntry = consumer.getVertexBuffer(stream0.bufferId);

        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `#version 300 es
            layout(location = 0) in vec2 aPos;
            layout(location = 1) in vec4 aColor;
            out vec4 vColor;
            void main() {
                vColor = aColor;
                gl_Position = vec4(aPos, 0.0, 1.0);
            }`);
        gl.compileShader(vs);

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `#version 300 es
            precision mediump float;
            in vec4 vColor;
            out vec4 fragColor;
            void main() { fragColor = vColor; }`);
        gl.compileShader(fs);

        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        gl.useProgram(prog);

        const vao = gl.createVertexArray();
        gl.bindVertexArray(vao);
        gl.bindBuffer(gl.ARRAY_BUFFER, vbEntry.glBuffer);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 2, gl.FLOAT, false, stream0.stride, stream0.offset + 0);
        gl.enableVertexAttribArray(1);
        gl.vertexAttribPointer(1, 4, gl.FLOAT, false, stream0.stride, stream0.offset + 8);

        gl.disable(gl.DEPTH_TEST);
        gl.disable(gl.CULL_FACE);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        const centerPixel = new Uint8Array(4);
        gl.readPixels(320, 240, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, centerPixel);

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            centerPixel: Array.from(centerPixel),
            stream0: stream0
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"Diagnostic VB draw failed: {result.get('error')}")
        self.assertEqual(result["stream0"]["bufferId"], 3)
        self.assertEqual(result["stream0"]["offset"], 48)
        self.assertEqual(result["stream0"]["stride"], 24)
        self.assertEqual(result["centerPixel"], [0, 255, 0, 255])

    def test_webgl2_index_buffer_lifecycle_and_gpu_readback(self):
        """Verifies 16-bit and 32-bit IndexBuffer allocation, bufferSubData upload, ELEMENT_ARRAY_BUFFER readback, and deletion."""
        script = """
        const cap = 4096;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // Create 16-bit IB (id=1, 32 bytes, D3DFMT_INDEX16=101) and 32-bit IB (id=2, 64 bytes, D3DFMT_INDEX32=102)
        producer.emitCreateIndexBuffer(1, 32, 0x08, 101, 1);
        producer.emitCreateIndexBuffer(2, 64, 0x208, 102, 0);

        // Upload 6 uint16 indices into IB 1 and 3 uint32 indices into IB 2
        producer.emitUpdateIndexBuffer(1, 0, new Uint16Array([0, 1, 2, 2, 3, 0]));
        producer.emitUpdateIndexBuffer(2, 8, new Uint32Array([1000, 2000, 3000]));
        producer.emitSetIndices(1);
        consumer.processCommands();

        const ib1 = consumer.getIndexBuffer(1);
        const ib2 = consumer.getIndexBuffer(2);

        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib1.glBuffer);
        const read16 = new Uint16Array(6);
        gl.getBufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, read16);

        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib2.glBuffer);
        const read32 = new Uint32Array(3);
        gl.getBufferSubData(gl.ELEMENT_ARRAY_BUFFER, 8, read32);

        const rawGlIb1 = ib1.glBuffer;
        const validBefore = gl.isBuffer(rawGlIb1);
        producer.emitDestroyIndexBuffer(1);
        consumer.processCommands();
        const validAfter = gl.isBuffer(rawGlIb1);

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            read16: Array.from(read16),
            read32: Array.from(read32),
            validBefore,
            validAfter,
            boundAfterDestroy: consumer.boundIndexBufferId
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"WebGL2 IB lifecycle failed: {result.get('error')}")
        self.assertEqual(result["read16"], [0, 1, 2, 2, 3, 0])
        self.assertEqual(result["read32"], [1000, 2000, 3000])
        self.assertTrue(result["validBefore"])
        self.assertFalse(result["validAfter"])
        self.assertEqual(result["boundAfterDestroy"], 0)

    def test_webgl2_end_to_end_textured_indexed_draw_pipeline(self):
        """Verifies full Phase 4.3 pipeline: VertexDecl + VB + IB + Texture + Sampler + DrawIndexedPrimitive in WebGL2."""
        script = """
        const cap = 8192;
        const ringBuf = new ArrayBuffer(64 + cap);
        const producer = D3D9.D3D9CommandProducer.initRing(ringBuf, 0, cap);
        const consumer = new D3D9.D3D9CommandConsumer(ringBuf, 0, { gl });

        // Bind a shader program that samples texture stage 0 and multiplies by vertex color
        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `#version 300 es
            layout(location = 0) in vec2 aPos;
            layout(location = 1) in vec2 aUV;
            out vec2 vUV;
            void main() {
                vUV = aUV;
                gl_Position = vec4(aPos, 0.0, 1.0);
            }`);
        gl.compileShader(vs);

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `#version 300 es
            precision mediump float;
            in vec2 vUV;
            uniform sampler2D uTex0;
            out vec4 fragColor;
            void main() {
                fragColor = texture(uTex0, vUV);
            }`);
        gl.compileShader(fs);

        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        gl.useProgram(prog);
        gl.uniform1i(gl.getUniformLocation(prog, 'uTex0'), 0);

        const vao = gl.createVertexArray();
        gl.bindVertexArray(vao);

        // 1. Create and bind Vertex Declaration:
        // attr 0: FLOAT2 (type=1) at offset 0 (POSITION)
        // attr 1: FLOAT2 (type=1) at offset 8 (TEXCOORD0)
        producer.emitCreateVertexDeclaration(1, [
            { stream: 0, offset: 0, type: 1, method: 0, usage: 0, usageIndex: 0 },
            { stream: 0, offset: 8, type: 1, method: 0, usage: 5, usageIndex: 0 },
        ]);
        producer.emitSetVertexDeclaration(1);

        // 2. Create and populate Vertex Buffer (4 vertices * 16 bytes = 64 bytes)
        producer.emitCreateVertexBuffer(1, 64, 0x08, 0, 1);
        const quadVerts = new Float32Array([
            -1.0, -1.0,  0.5, 0.5,
             1.0, -1.0,  0.5, 0.5,
             1.0,  1.0,  0.5, 0.5,
            -1.0,  1.0,  0.5, 0.5,
        ]);
        producer.emitUpdateVertexBuffer(1, 0, quadVerts);
        producer.emitSetStreamSource(0, 1, 0, 16);

        // 3. Create and populate Index Buffer (6 uint16 indices = 2 triangles)
        producer.emitCreateIndexBuffer(1, 12, 0x08, 101, 1);
        producer.emitUpdateIndexBuffer(1, 0, new Uint16Array([0, 1, 2, 0, 2, 3]));
        producer.emitSetIndices(1);

        // 4. Create and populate 2x2 A8R8G8B8 texture filled with ProStreet Gold (R=240, G=180, B=20, A=255)
        // In D3DFMT_A8R8G8B8 little-endian memory order: [B=20, G=180, R=240, A=255]
        producer.emitCreateTexture(1, 2, 2, 1, 0, 21, 1);
        const texBytes = new Uint8Array([
            20, 180, 240, 255,   20, 180, 240, 255,
            20, 180, 240, 255,   20, 180, 240, 255,
        ]);
        producer.emitUpdateTexture(1, 0, 8, 2, 2, texBytes);
        producer.emitSetSamplerState(0, 1, 3); // ADDRESSU = CLAMP
        producer.emitSetSamplerState(0, 2, 3); // ADDRESSV = CLAMP
        producer.emitSetSamplerState(0, 5, 1); // MAGFILTER = POINT
        producer.emitSetSamplerState(0, 6, 1); // MINFILTER = POINT
        producer.emitSetTexture(0, 1);

        // 5. Disable culling and depth test, clear to black, and issue DRAW_INDEXED_PRIMITIVE via command stream
        producer.emitSetRenderState(22, 1); // CULLMODE = NONE
        producer.emitSetRenderState(7, 0);  // ZENABLE = FALSE
        producer.emitBeginScene();
        producer.emitClear(1, 0xFF000000, 1.0, 0);
        producer.emitDrawIndexedPrimitive(4, 0, 0, 4, 0, 2); // D3DPT_TRIANGLELIST = 4, 2 tris
        producer.emitEndScene();
        producer.emitPresent(0, 0, 640, 480);

        consumer.processCommands();

        const centerPixel = new Uint8Array(4);
        gl.readPixels(320, 240, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, centerPixel);

        document.getElementById('result').innerText = JSON.stringify({
            success: true,
            drawCallsExecuted: consumer.drawCallsExecuted,
            presentedFrames: consumer.presentedFrames,
            centerPixel: Array.from(centerPixel)
        });
        """

        result = self.run_chrome_webgl2(script)
        self.assertTrue(result.get("success"), f"End-to-end textured indexed draw failed: {result.get('error')}")
        self.assertEqual(result["drawCallsExecuted"], 1)
        self.assertEqual(result["presentedFrames"], 1)
        self.assertEqual(result["centerPixel"], [240, 180, 20, 255])


if __name__ == "__main__":
    unittest.main()
