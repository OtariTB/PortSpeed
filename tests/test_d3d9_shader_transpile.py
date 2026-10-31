"""Reproducible tests for Direct3D9 shader translation to GLSL ES 3.00 and WebGL2 verification."""

import ctypes
import json
import math
import re
import struct
import subprocess
import unittest
from pathlib import Path

from tools.build_win32_shims import EXE_PATH
from tools.inventory_effects import parse_pe_resources
from tools.d3dx9_effect import D3DX9EffectParser


class MOJOSHADER_parseData(ctypes.Structure):
    _fields_ = [
        ('error_count', ctypes.c_int),
        ('errors', ctypes.c_void_p),
        ('profile', ctypes.c_char_p),
        ('output', ctypes.c_char_p),
        ('output_len', ctypes.c_int),
        ('instruction_count', ctypes.c_int),
    ]


def translate_d3d9_to_glsl(sh_bytes: bytes, profile: str = "glsl120") -> tuple[str, int]:
    """Translate D3D9 shader bytecode using MojoShader native library."""
    dll_path = Path("tools/lib/mojoshader.dll")
    if not dll_path.exists():
        raise FileNotFoundError(f"mojoshader.dll not found at {dll_path}")

    dll = ctypes.CDLL(str(dll_path.resolve()))
    dll.MOJOSHADER_parse.restype = ctypes.POINTER(MOJOSHADER_parseData)

    res = dll.MOJOSHADER_parse(
        profile.encode('utf-8'),
        sh_bytes,
        len(sh_bytes),
        None, 0,
        None, 0,
        None, None, None
    )

    if not res:
        raise RuntimeError("MOJOSHADER_parse returned NULL")

    pdata = res.contents
    if pdata.error_count > 0:
        return "", pdata.error_count

    return pdata.output.decode('latin1'), 0


def adapt_to_glsl_es_300(glsl120_source: str, stage: str = "vertex") -> str:
    """Adapt MojoShader GLSL 1.20 output into GLSL ES 3.00 for WebGL2."""
    lines = glsl120_source.strip().splitlines()
    out_lines = [
        "#version 300 es",
        "precision highp float;",
        "precision mediump int;",
    ]
    if stage == "fragment":
        out_lines.append("out vec4 oColor;")

    for line in lines:
        s = line.strip()
        if s.startswith("#version"):
            continue
        elif s.startswith("attribute "):
            out_lines.append(line.replace("attribute ", "in "))
        elif s.startswith("varying "):
            if stage == "vertex":
                out_lines.append(line.replace("varying ", "out "))
            else:
                out_lines.append(line.replace("varying ", "in "))
        elif "gl_FragColor" in line:
            out_lines.append(line.replace("gl_FragColor", "oColor"))
        elif "texture2D(" in line:
            out_lines.append(line.replace("texture2D(", "texture("))
        else:
            out_lines.append(line)

    return "\n".join(out_lines) + "\n"


def adapt_vs_paired(glsl120_source: str) -> str:
    """Diagnostic harness helper: augment vs_2_0 with synthetic varyings to test ps_2_0.

    IMPORTANT AUDIT NOTE:
    The original vs_2_0 shader in IDI_STANDARD_FX belongs to the depth pass and only
    generates oPos and oT0.xy (Z, W). It does NOT natively output vFrontColor or vTexCoord1.
    This helper injects synthetic varyings solely to isolate and exercise ps_2_0 instruction
    execution in WebGL2 without translating the separate authentic standard VS (vs_1_1).
    """
    lines = [
        "#version 300 es",
        "precision highp float;",
        "precision mediump int;",
        "in vec4 a_texcoord0;",
        "in vec4 a_texcoord1;",
        "in vec4 a_color;",
        "out vec4 vFrontColor;",
        "out vec4 vTexCoord1;",
    ]
    for line in glsl120_source.strip().splitlines():
        if line.startswith("#version"):
            continue
        elif line.startswith("attribute "):
            lines.append(line.replace("attribute ", "in "))
        elif line.startswith("varying "):
            lines.append(line.replace("varying ", "out "))
        else:
            lines.append(line)

    src = "\n".join(lines)
    main_end = src.rfind("}")
    assigns = """
    vTexCoord0 = a_texcoord0;
    vTexCoord1 = a_texcoord1;
    vFrontColor = a_color;
"""
    return src[:main_end] + assigns + "}\n"


def simulate_d3d9_vs_2_0(
    v0: list[float],
    matrix_rows: list[list[float]],
    pos_fixup: list[float] = [1.0, 1.0, 0.0, 0.0]
) -> tuple[list[float], list[float]]:
    """Simulate authentic D3D9 vs_2_0 execution + MojoShader position fixup."""
    c4 = [1.0, 0.0, 0.0, 0.0]
    r0 = [
        v0[0] * c4[0] + c4[1],
        v0[1] * c4[0] + c4[1],
        v0[2] * c4[0] + c4[1],
        v0[0] * c4[1] + c4[0],
    ]

    c0, c1, c2, c3 = matrix_rows

    opos_x = sum(r0[i] * c0[i] for i in range(4))
    opos_y = sum(r0[i] * c1[i] for i in range(4))
    r1_x = sum(r0[i] * c2[i] for i in range(4))
    r1_y = sum(r0[i] * c3[i] for i in range(4))

    opos_z = r1_x
    opos_w = r1_y
    ot0_x = r1_x
    ot0_y = r1_y

    gl_pos_x = opos_x + pos_fixup[2] * opos_w
    gl_pos_y = opos_y * pos_fixup[1] + pos_fixup[3] * opos_w
    gl_pos_z = opos_z * 2.0 - opos_w
    gl_pos_w = opos_w

    return [gl_pos_x, gl_pos_y, gl_pos_z, gl_pos_w], [ot0_x, ot0_y]


def simulate_d3d9_ps_2_0_standard(
    diffuse_rgba: list[float],
    opacity_rgba: list[float],
    vertex_color: list[float],
) -> list[float]:
    """CPU simulation of authentic IDI_STANDARD_FX ps_2_0 (offset 0x0a68).

    Instruction sequence:
      texld r0, t1, s1       (sample OPACITY_SAMPLER at t1.xy)
      texld r1, t0, s0       (sample DIFFUSE_SAMPLER at t0.xy)
      mul r1.w, r0.w, r1.w   (combine diffuse alpha with opacity alpha)
      mul r0, r1, v0         (modulate diffuse RGB and combined alpha by vertex color)
      mov oC0, r0            (write fragment color)
    """
    r0 = list(opacity_rgba)
    r1 = list(diffuse_rgba)
    r1[3] = r0[3] * r1[3]
    return [r1[i] * vertex_color[i] for i in range(4)]


def simulate_alpha_blend(src_rgba: list[float], dst_rgba: list[float]) -> list[float]:
    """CPU simulation of gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)."""
    src_a = src_rgba[3]
    out_rgb = [src_rgba[i] * src_a + dst_rgba[i] * (1.0 - src_a) for i in range(3)]
    out_a = src_a * src_a + dst_rgba[3] * (1.0 - src_a)
    return [out_rgb[0], out_rgb[1], out_rgb[2], out_a]


class TestD3D9ShaderTranslation(unittest.TestCase):
    """Test suite for validating MojoShader D3D9 translation and WebGL2 execution."""

    @classmethod
    def setUpClass(cls):
        """Extract shaders from authentic IDI_STANDARD_FX."""
        cls.exe_bytes = EXE_PATH.read_bytes()
        entries = parse_pe_resources(cls.exe_bytes)
        std_entry = [e for e in entries if e[0] == 'IDI_STANDARD_FX'][0]
        cls.raw_fx = cls.exe_bytes[std_entry[3] : std_entry[3] + std_entry[1]]
        parser = D3DX9EffectParser(cls.raw_fx)
        cls.effect = parser.parse()
        cls.vs20 = [s for s in cls.effect.shaders if s.target == 'vs_2_0'][0]
        cls.vs11 = [s for s in cls.effect.shaders if s.target.startswith('vs_1')][0]
        cls.ps20_std = [s for s in cls.effect.shaders if s.target == 'ps_2_0' and len(s.constants) > 0][0]
        cls.ps20_depth = [s for s in cls.effect.shaders if s.target == 'ps_2_0' and len(s.constants) == 0][0]
        cls.chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

    def test_mojoshader_dll_available(self):
        """Verify that mojoshader.dll is present and exports MOJOSHADER_parse."""
        dll_path = Path("tools/lib/mojoshader.dll")
        self.assertTrue(dll_path.exists(), f"mojoshader.dll missing at {dll_path}")
        dll = ctypes.CDLL(str(dll_path.resolve()))
        self.assertTrue(hasattr(dll, "MOJOSHADER_parse"))

    def test_translate_vs_2_0_authentic(self):
        """Verify that genuine vs_2_0 from IDI_STANDARD_FX translates with zero errors."""
        glsl_src, err_count = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")
        self.assertEqual(err_count, 0)
        self.assertGreater(len(glsl_src), 100)

        self.assertIn("vs_uniforms_vec4[4]", glsl_src)
        self.assertIn("posFixup", glsl_src)
        self.assertIn("attribute vec4 vs_v0;", glsl_src)
        self.assertIn("varying vec4 vTexCoord0;", glsl_src)
        self.assertIn("#define vs_oPos gl_Position", glsl_src)
        self.assertIn("vs_oPos.x = dot(vs_r0, vs_c0);", glsl_src)
        self.assertIn("vs_oPos.y = dot(vs_r0, vs_c1);", glsl_src)
        self.assertIn("gl_Position.z = gl_Position.z * 2.0 - gl_Position.w;", glsl_src)

    def test_glsl_es_300_adaptation(self):
        """Verify conversion from GLSL 1.20 to GLSL ES 3.00."""
        glsl_src, _ = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")
        es3_src = adapt_to_glsl_es_300(glsl_src, "vertex")

        self.assertTrue(es3_src.startswith("#version 300 es\nprecision highp float;\nprecision mediump int;"))
        self.assertIn("in vec4 vs_v0;", es3_src)
        self.assertIn("out vec4 vTexCoord0;", es3_src)
        self.assertNotIn("attribute ", es3_src)
        self.assertNotIn("varying ", es3_src)

    def test_d3d9_instruction_output_assignments_and_semantics(self):
        """Verify that vs_2_0 instruction tokens exactly map to WVP transform and oT0.xy depth copy."""
        glsl_src, _ = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")

        self.assertIn("vs_r0 = (vs_v0.xyzx * vs_c4.xxxy) + vs_c4.yyyx;", glsl_src)
        self.assertIn("vs_oPos.x = dot(vs_r0, vs_c0);", glsl_src)
        self.assertIn("vs_oPos.y = dot(vs_r0, vs_c1);", glsl_src)
        self.assertIn("vs_r1.x = dot(vs_r0, vs_c2);", glsl_src)
        self.assertIn("vs_r1.y = dot(vs_r0, vs_c3);", glsl_src)
        self.assertIn("vs_oPos.zw = vs_r1.xy;", glsl_src)
        self.assertIn("vs_oT0.xy = vs_r1.xy;", glsl_src)
        self.assertIn("gl_Position.y = gl_Position.y * posFixup.y;", glsl_src)
        self.assertIn("gl_Position.xy += posFixup.zw * gl_Position.ww;", glsl_src)
        self.assertIn("gl_Position.z = gl_Position.z * 2.0 - gl_Position.w;", glsl_src)

    def test_webgl2_headless_chrome_compilation(self):
        """Verify that translated GLSL ES 3.00 shader compiles and links in real WebGL2."""
        if not self.chrome_path.exists():
            self.skipTest(f"Chrome not found at {self.chrome_path}")

        glsl_src, _ = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")
        es3_src = adapt_to_glsl_es_300(glsl_src, "vertex")

        html_content = f"""<!DOCTYPE html>
<html><body><pre id="result">WAIT</pre><script>
window.addEventListener('DOMContentLoaded', () => {{
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) {{
        document.getElementById('result').innerText = JSON.stringify({{ success: false, error: 'No WebGL2' }});
        return;
    }}
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, `{es3_src}`);
    gl.compileShader(vs);
    const compiled = gl.getShaderParameter(vs, gl.COMPILE_STATUS);
    const infoLog = gl.getShaderInfoLog(vs);

    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, `#version 300 es
precision mediump float;
in vec4 vTexCoord0;
out vec4 fragColor;
void main() {{ fragColor = vTexCoord0; }}
`);
    gl.compileShader(fs);

    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    const linked = gl.getProgramParameter(prog, gl.LINK_STATUS);

    const activeAttribs = [];
    for (let i = 0; i < gl.getProgramParameter(prog, gl.ACTIVE_ATTRIBUTES); i++) {{
        activeAttribs.push(gl.getActiveAttrib(prog, i).name);
    }}

    const activeUniforms = [];
    for (let i = 0; i < gl.getProgramParameter(prog, gl.ACTIVE_UNIFORMS); i++) {{
        activeUniforms.push(gl.getActiveUniform(prog, i).name);
    }}

    document.getElementById('result').innerText = JSON.stringify({{
        success: compiled && linked,
        compiled: compiled,
        linked: linked,
        infoLog: infoLog,
        activeAttribs: activeAttribs,
        activeUniforms: activeUniforms
    }});
}});
</script></body></html>
"""
        test_html = Path("tools/temp_webgl2_test.html")
        test_html.write_text(html_content, encoding="utf-8")

        try:
            cmd = [
                str(self.chrome_path),
                "--headless=new",
                "--disable-gpu-sandbox",
                "--use-gl=angle",
                "--dump-dom",
                f"file:///{test_html.resolve().as_posix()}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
            self.assertIsNotNone(match, f"No result in DOM: {res.stdout[:400]}")
            result = json.loads(match.group(1))

            self.assertTrue(result.get("success"), f"WebGL2 compilation failed: {result.get('infoLog')}")
            self.assertTrue(result.get("compiled"))
            self.assertTrue(result.get("linked"))
            self.assertIn("vs_v0", result.get("activeAttribs", []))
            self.assertIn("vs_uniforms_vec4[0]", result.get("activeUniforms", []))
            self.assertIn("posFixup", result.get("activeUniforms", []))
        finally:
            if test_html.exists():
                test_html.unlink()

    def test_webgl2_transform_feedback_vs_cpu_simulation(self):
        """Execute translated shader in WebGL2 via Transform Feedback and compare against CPU simulation."""
        if not self.chrome_path.exists():
            self.skipTest(f"Chrome not found at {self.chrome_path}")

        glsl_src, _ = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")
        es3_src = adapt_to_glsl_es_300(glsl_src, "vertex")

        vertices = [
            [0.0, 0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 1.0, 1.0],
            [1.5, -2.5, 3.25, 1.0],
            [-10.0, 5.0, 20.0, 1.0],
        ]
        flat_verts = [x for v in vertices for x in v]

        fov = 60.0 * math.pi / 180.0
        aspect = 16.0 / 9.0
        near = 0.5
        far = 1000.0
        f = 1.0 / math.tan(fov / 2.0)

        c0 = [f / aspect, 0.0, 0.0, 0.0]
        c1 = [0.0, f, 0.0, 0.0]
        c2 = [0.0, 0.0, far / (far - near), 1.0]
        c3 = [0.0, 0.0, -near * far / (far - near), 0.0]
        matrix_rows = [c0, c1, c2, c3]
        matrix_flat = c0 + c1 + c2 + c3
        pos_fixup = [1.0, 1.0, 0.0, 0.0]

        cpu_gl_pos = []
        cpu_ot0 = []
        for v in vertices:
            gp, ot = simulate_d3d9_vs_2_0(v, matrix_rows, pos_fixup)
            cpu_gl_pos.append(gp)
            cpu_ot0.append(ot)

        html_content = f"""<!DOCTYPE html>
<html><body><pre id="result">WAIT</pre><script>
window.addEventListener('DOMContentLoaded', () => {{
    try {{
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl2');
        if (!gl) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'No WebGL2' }});
            return;
        }}

        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `{es3_src}`);
        gl.compileShader(vs);

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `#version 300 es
        precision mediump float;
        in vec4 vTexCoord0;
        out vec4 fragColor;
        void main() {{ fragColor = vTexCoord0; }}
        `);
        gl.compileShader(fs);

        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.transformFeedbackVaryings(prog, ['gl_Position', 'vTexCoord0'], gl.SEPARATE_ATTRIBS);
        gl.linkProgram(prog);

        gl.useProgram(prog);

        const uMat = gl.getUniformLocation(prog, 'vs_uniforms_vec4[0]');
        gl.uniform4fv(uMat, new Float32Array({json.dumps(matrix_flat)}));

        const uFixup = gl.getUniformLocation(prog, 'posFixup');
        gl.uniform4fv(uFixup, new Float32Array({json.dumps(pos_fixup)}));

        const inBuf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, inBuf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(flat_verts)}), gl.STATIC_DRAW);

        const posLoc = gl.getAttribLocation(prog, 'vs_v0');
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 4, gl.FLOAT, false, 0, 0);

        const numVerts = {len(vertices)};

        const outPosBuf = gl.createBuffer();
        gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, outPosBuf);
        gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER, numVerts * 4 * 4, gl.STATIC_READ);

        const outT0Buf = gl.createBuffer();
        gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, outT0Buf);
        gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER, numVerts * 4 * 4, gl.STATIC_READ);

        const tf = gl.createTransformFeedback();
        gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, tf);
        gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, outPosBuf);
        gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 1, outT0Buf);

        gl.enable(gl.RASTERIZER_DISCARD);
        gl.beginTransformFeedback(gl.POINTS);
        gl.drawArrays(gl.POINTS, 0, numVerts);
        gl.endTransformFeedback();
        gl.disable(gl.RASTERIZER_DISCARD);

        const outPos = new Float32Array(numVerts * 4);
        gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, outPosBuf);
        gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER, 0, outPos);

        const outT0 = new Float32Array(numVerts * 4);
        gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, outT0Buf);
        gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER, 0, outT0);

        document.getElementById('result').innerText = JSON.stringify({{
            success: true,
            gl_Position: Array.from(outPos),
            vTexCoord0: Array.from(outT0)
        }});
    }} catch (e) {{
        document.getElementById('result').innerText = JSON.stringify({{ error: e.toString() }});
    }}
}});
</script></body></html>
"""
        test_html = Path("tools/temp_tf_test.html")
        test_html.write_text(html_content, encoding="utf-8")

        try:
            cmd = [
                str(self.chrome_path),
                "--headless=new",
                "--disable-gpu-sandbox",
                "--use-gl=angle",
                "--dump-dom",
                f"file:///{test_html.resolve().as_posix()}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
            self.assertIsNotNone(match, f"No result in DOM: {res.stdout[:400]}")
            result = json.loads(match.group(1))

            self.assertTrue(result.get("success"), f"WebGL2 TransformFeedback failed: {result.get('error')}")
            gpu_gl_pos = result["gl_Position"]
            gpu_ot0 = result["vTexCoord0"]

            for i in range(len(vertices)):
                cg = cpu_gl_pos[i]
                gg = gpu_gl_pos[i * 4 : (i + 1) * 4]
                co = cpu_ot0[i]
                go = gpu_ot0[i * 4 : (i + 1) * 4]

                for comp in range(4):
                    diff = abs(cg[comp] - gg[comp])
                    self.assertLess(
                        diff, 1e-5,
                        f"gl_Position mismatch at vertex {i}[{comp}]: CPU={cg[comp]} vs GPU={gg[comp]}, diff={diff}"
                    )

                for comp in range(2):
                    diff = abs(co[comp] - go[comp])
                    self.assertLess(
                        diff, 1e-5,
                        f"vTexCoord0 mismatch at vertex {i}[{comp}]: CPU={co[comp]} vs GPU={go[comp]}, diff={diff}"
                    )
        finally:
            if test_html.exists():
                test_html.unlink()

    def test_webgl2_rasterization_and_fragment_reception(self):
        """Verify triangle rasterization and fragment shader reception of vTexCoord0."""
        if not self.chrome_path.exists():
            self.skipTest(f"Chrome not found at {self.chrome_path}")

        glsl_src, _ = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")
        es3_src = adapt_to_glsl_es_300(glsl_src, "vertex")

        tri_verts = [
            -0.5, -0.5, 0.5, 1.0,
             0.5, -0.5, 0.5, 1.0,
             0.0,  0.5, 0.5, 1.0,
        ]
        c0 = [1.0, 0.0, 0.0, 0.0]
        c1 = [0.0, 1.0, 0.0, 0.0]
        c2 = [0.0, 0.0, 1.0, 0.0]
        c3 = [0.0, 0.0, 0.0, 1.0]
        matrix_flat = c0 + c1 + c2 + c3
        pos_fixup = [1.0, 1.0, 0.0, 0.0]

        html_content = f"""<!DOCTYPE html>
<html><body><pre id="result">WAIT</pre><script>
window.addEventListener('DOMContentLoaded', () => {{
    try {{
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const gl = canvas.getContext('webgl2');
        if (!gl) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'No WebGL2' }});
            return;
        }}

        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `{es3_src}`);
        gl.compileShader(vs);

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `#version 300 es
        precision mediump float;
        in vec4 vTexCoord0;
        out vec4 fragColor;
        void main() {{
            fragColor = vec4(vTexCoord0.x, 0.25, 0.75, 1.0);
        }}
        `);
        gl.compileShader(fs);

        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);

        gl.useProgram(prog);

        const uMat = gl.getUniformLocation(prog, 'vs_uniforms_vec4[0]');
        gl.uniform4fv(uMat, new Float32Array({json.dumps(matrix_flat)}));

        const uFixup = gl.getUniformLocation(prog, 'posFixup');
        gl.uniform4fv(uFixup, new Float32Array({json.dumps(pos_fixup)}));

        const inBuf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, inBuf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_verts)}), gl.STATIC_DRAW);

        const posLoc = gl.getAttribLocation(prog, 'vs_v0');
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 4, gl.FLOAT, false, 0, 0);

        gl.viewport(0, 0, 64, 64);
        gl.clearColor(0.0, 0.0, 0.0, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        gl.drawArrays(gl.TRIANGLES, 0, 3);

        const centerPixel = new Uint8Array(4);
        gl.readPixels(32, 32, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, centerPixel);

        const cornerPixel = new Uint8Array(4);
        gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, cornerPixel);

        document.getElementById('result').innerText = JSON.stringify({{
            success: true,
            centerPixel: Array.from(centerPixel),
            cornerPixel: Array.from(cornerPixel)
        }});
    }} catch (e) {{
        document.getElementById('result').innerText = JSON.stringify({{ error: e.toString() }});
    }}
}});
</script></body></html>
"""
        test_html = Path("tools/temp_raster_test.html")
        test_html.write_text(html_content, encoding="utf-8")

        try:
            cmd = [
                str(self.chrome_path),
                "--headless=new",
                "--disable-gpu-sandbox",
                "--use-gl=angle",
                "--dump-dom",
                f"file:///{test_html.resolve().as_posix()}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
            self.assertIsNotNone(match, f"No result in DOM: {res.stdout[:400]}")
            result = json.loads(match.group(1))

            self.assertTrue(result.get("success"), f"Raster test failed: {result.get('error')}")
            center = result["centerPixel"]
            corner = result["cornerPixel"]

            self.assertAlmostEqual(center[0], 127.5, delta=2.0)
            self.assertAlmostEqual(center[1], 64.0, delta=2.0)
            self.assertAlmostEqual(center[2], 191.0, delta=2.0)
            self.assertEqual(center[3], 255)
            self.assertEqual(corner, [0, 0, 0, 255])
        finally:
            if test_html.exists():
                test_html.unlink()

    def test_malformed_shader_bytecode_rejection(self):
        """Verify that malformed shader bytecodes are rejected by MojoShader with error count > 0."""
        corrupt = b"\x00\x00\x00\x00" * 8
        glsl_src, err_count = translate_d3d9_to_glsl(corrupt, "glsl120")
        self.assertGreater(err_count, 0)
        self.assertEqual(glsl_src, "")

    def test_identify_authentic_ps_2_0_in_standard_technique(self):
        """Trace pass references in IDI_STANDARD_FX to identify standard technique ps_2_0."""
        # 1. Verify technique standard pass p0 state assignments
        # In IDI_STANDARD_FX binary:
        # Pass p0 for technique standard is at offset 0x0790
        # State assignment at 0x07c0: D3DRS_PIXELSHADER (147) points to object at 0x05e8
        # Object 0x05e8 has parameter type 15 (D3DXPT_PIXELSHADER)
        p0_std_pass_off = 0x0790
        p0_name_ptr = struct.unpack_from('<I', self.raw_fx, p0_std_pass_off)[0]
        # At p0_name_ptr is string length (0x00000003) followed by "p0\x00"
        self.assertEqual(self.raw_fx[p0_name_ptr + 4 : p0_name_ptr + 7], b'p0\x00')

        # D3DRS_PIXELSHADER state check
        ps_state_type = struct.unpack_from('<I', self.raw_fx, 0x07c0)[0]
        self.assertEqual(ps_state_type, 147, "Expected D3DRS_PIXELSHADER (147)")

        # 2. Verify authentic standard ps_2_0 properties
        self.assertEqual(self.ps20_std.target, "ps_2_0")
        self.assertEqual(self.ps20_std.offset, 0x0a68)
        self.assertEqual(self.ps20_std.length, 320)
        self.assertEqual(len(self.ps20_std.constants), 2)

        const_names = {c.name: c for c in self.ps20_std.constants}
        self.assertIn("DIFFUSE_SAMPLER", const_names)
        self.assertEqual(const_names["DIFFUSE_SAMPLER"].register_set, "Sampler")
        self.assertEqual(const_names["DIFFUSE_SAMPLER"].register_index, 0)

        self.assertIn("OPACITY_SAMPLER", const_names)
        self.assertEqual(const_names["OPACITY_SAMPLER"].register_set, "Sampler")
        self.assertEqual(const_names["OPACITY_SAMPLER"].register_index, 1)

    def test_translate_ps_2_0_standard_glsl_es_300(self):
        """Translate authentic standard ps_2_0 and verify GLSL ES 3.00 adaptation."""
        glsl_src, err_count = translate_d3d9_to_glsl(self.ps20_std.bytecode, "glsl120")
        self.assertEqual(err_count, 0)
        self.assertGreater(len(glsl_src), 50)

        # MojoShader GLSL 1.20 checks
        self.assertIn("uniform sampler2D ps_s0;", glsl_src)
        self.assertIn("uniform sampler2D ps_s1;", glsl_src)
        self.assertIn("ps_r0 = texture2D(ps_s1, ps_t1.xy);", glsl_src)
        self.assertIn("ps_r1 = texture2D(ps_s0, ps_t0.xy);", glsl_src)
        self.assertIn("ps_r1.w = ps_r0.w * ps_r1.w;", glsl_src)
        self.assertIn("ps_r0 = ps_r1 * ps_v0;", glsl_src)

        # GLSL ES 3.00 adaptation checks
        es3_src = adapt_to_glsl_es_300(glsl_src, stage="fragment")
        self.assertTrue(es3_src.startswith("#version 300 es\nprecision highp float;\nprecision mediump int;\nout vec4 oColor;"))
        self.assertIn("in vec4 vFrontColor;", es3_src)
        self.assertIn("in vec4 vTexCoord0;", es3_src)
        self.assertIn("in vec4 vTexCoord1;", es3_src)
        self.assertIn("texture(ps_s1", es3_src)
        self.assertIn("texture(ps_s0", es3_src)
        self.assertNotIn("texture2D(", es3_src)
        self.assertNotIn("gl_FragColor", es3_src)

    def test_unmodified_vs_2_0_interface_mismatch_with_standard_ps_2_0(self):
        """Authenticity audit: prove unmodified vs_2_0 lacks varyings required by standard ps_2_0.

        Authentic vs_2_0 outputs only gl_Position and vTexCoord0.
        Authentic ps_2_0 requires vFrontColor, vTexCoord0, and vTexCoord1.
        Linking them in WebGL2 without synthetic interface augmentation must fail.
        """
        if not self.chrome_path.exists():
            self.skipTest(f"Chrome not found at {self.chrome_path}")

        vs_glsl, _ = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")
        vs_es3 = adapt_to_glsl_es_300(vs_glsl, stage="vertex")

        ps_glsl, _ = translate_d3d9_to_glsl(self.ps20_std.bytecode, "glsl120")
        ps_es3 = adapt_to_glsl_es_300(ps_glsl, stage="fragment")

        html_content = f"""<!DOCTYPE html>
<html><body><pre id="result">WAIT</pre><script>
window.addEventListener('DOMContentLoaded', () => {{
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) {{
        document.getElementById('result').innerText = JSON.stringify({{ error: 'No WebGL2' }});
        return;
    }}

    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, `{vs_es3}`);
    gl.compileShader(vs);

    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, `{ps_es3}`);
    gl.compileShader(fs);

    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    const linked = gl.getProgramParameter(prog, gl.LINK_STATUS);
    const log = gl.getProgramInfoLog(prog);

    document.getElementById('result').innerText = JSON.stringify({{
        linked: linked,
        log: log
    }});
}});
</script></body></html>
"""
        test_html = Path("tools/temp_audit_link.html")
        test_html.write_text(html_content, encoding="utf-8")

        try:
            cmd = [
                str(self.chrome_path),
                "--headless=new",
                "--disable-gpu-sandbox",
                "--use-gl=angle",
                "--dump-dom",
                f"file:///{test_html.resolve().as_posix()}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
            self.assertIsNotNone(match, f"No result in DOM: {res.stdout[:400]}")
            result = json.loads(match.group(1))

            # The unmodified pair MUST fail to link due to missing varyings
            self.assertFalse(result.get("linked"), "Unmodified vs_2_0 unexpectedly linked with standard ps_2_0")
            self.assertIn("vFrontColor", result.get("log", ""))
        finally:
            if test_html.exists():
                test_html.unlink()

    def test_webgl2_pixel_shader_execution_with_diagnostic_textures(self):
        """Execute authentic ps_2_0 with diagnostic textures in WebGL2 and compare against CPU simulation.

        NOTE: Uses adapt_vs_paired to supply synthetic varying inputs so that ps_2_0's
        internal arithmetic and sampler texture instructions can be validated in isolation.
        """
        if not self.chrome_path.exists():
            self.skipTest(f"Chrome not found at {self.chrome_path}")

        vs_glsl, _ = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")
        vs_es3 = adapt_vs_paired(vs_glsl)

        ps_glsl, _ = translate_d3d9_to_glsl(self.ps20_std.bytecode, "glsl120")
        ps_es3 = adapt_to_glsl_es_300(ps_glsl, stage="fragment")

        # Test case:
        # Diffuse texture: 2x2 solid RGBA(0.8, 0.4, 0.2, 0.8) -> [204, 102, 51, 204]
        diffuse_texels = [204, 102, 51, 204] * 4
        # Opacity texture: 2x2 solid RGBA(0.0, 0.0, 0.0, 0.5) -> [0, 0, 0, 128]
        opacity_texels = [0, 0, 0, 128] * 4
        # Vertex color: RGBA(0.5, 0.8, 1.0, 1.0)
        vert_color = [0.5, 0.8, 1.0, 1.0]

        # CPU Reference evaluation
        diffuse_norm = [c / 255.0 for c in [204, 102, 51, 204]]
        opacity_norm = [c / 255.0 for c in [0, 0, 0, 128]]
        cpu_rgba = simulate_d3d9_ps_2_0_standard(diffuse_norm, opacity_norm, vert_color)
        exp_pixel = [round(c * 255.0) for c in cpu_rgba]

        # Geometry: Triangle spanning the center of a 64x64 framebuffer
        tri_verts = [
            -0.5, -0.5, 0.5, 1.0,
             0.5, -0.5, 0.5, 1.0,
             0.0,  0.5, 0.5, 1.0,
        ]
        tri_tc0 = [0.5, 0.5, 0.0, 0.0] * 3
        tri_tc1 = [0.5, 0.5, 0.0, 0.0] * 3
        tri_colors = vert_color * 3

        c0 = [1.0, 0.0, 0.0, 0.0]
        c1 = [0.0, 1.0, 0.0, 0.0]
        c2 = [0.0, 0.0, 1.0, 0.0]
        c3 = [0.0, 0.0, 0.0, 1.0]
        matrix_flat = c0 + c1 + c2 + c3
        pos_fixup = [1.0, 1.0, 0.0, 0.0]

        html_content = f"""<!DOCTYPE html>
<html><body><pre id="result">WAIT</pre><script>
window.addEventListener('DOMContentLoaded', () => {{
    try {{
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const gl = canvas.getContext('webgl2');
        if (!gl) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'No WebGL2' }});
            return;
        }}

        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `{vs_es3}`);
        gl.compileShader(vs);

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `{ps_es3}`);
        gl.compileShader(fs);

        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'Link: ' + gl.getProgramInfoLog(prog) }});
            return;
        }}

        gl.useProgram(prog);

        const uMat = gl.getUniformLocation(prog, 'vs_uniforms_vec4[0]');
        gl.uniform4fv(uMat, new Float32Array({json.dumps(matrix_flat)}));

        const uFixup = gl.getUniformLocation(prog, 'posFixup');
        gl.uniform4fv(uFixup, new Float32Array({json.dumps(pos_fixup)}));

        // Diffuse Texture (s0)
        const t0 = gl.createTexture();
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, t0);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 2, 2, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array({json.dumps(diffuse_texels)}));
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        const uS0 = gl.getUniformLocation(prog, 'ps_s0');
        gl.uniform1i(uS0, 0);

        // Opacity Texture (s1)
        const t1 = gl.createTexture();
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, t1);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 2, 2, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array({json.dumps(opacity_texels)}));
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        const uS1 = gl.getUniformLocation(prog, 'ps_s1');
        gl.uniform1i(uS1, 1);

        // Vertex Attributes
        const vBuf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, vBuf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_verts)}), gl.STATIC_DRAW);
        const posLoc = gl.getAttribLocation(prog, 'vs_v0');
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 4, gl.FLOAT, false, 0, 0);

        const tc0Buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, tc0Buf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_tc0)}), gl.STATIC_DRAW);
        const tc0Loc = gl.getAttribLocation(prog, 'a_texcoord0');
        gl.enableVertexAttribArray(tc0Loc);
        gl.vertexAttribPointer(tc0Loc, 4, gl.FLOAT, false, 0, 0);

        const tc1Buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, tc1Buf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_tc1)}), gl.STATIC_DRAW);
        const tc1Loc = gl.getAttribLocation(prog, 'a_texcoord1');
        gl.enableVertexAttribArray(tc1Loc);
        gl.vertexAttribPointer(tc1Loc, 4, gl.FLOAT, false, 0, 0);

        const colBuf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, colBuf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_colors)}), gl.STATIC_DRAW);
        const colLoc = gl.getAttribLocation(prog, 'a_color');
        gl.enableVertexAttribArray(colLoc);
        gl.vertexAttribPointer(colLoc, 4, gl.FLOAT, false, 0, 0);

        gl.viewport(0, 0, 64, 64);
        gl.clearColor(0.0, 0.0, 0.0, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        gl.drawArrays(gl.TRIANGLES, 0, 3);

        const centerPixel = new Uint8Array(4);
        gl.readPixels(32, 32, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, centerPixel);

        const cornerPixel = new Uint8Array(4);
        gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, cornerPixel);

        document.getElementById('result').innerText = JSON.stringify({{
            success: true,
            centerPixel: Array.from(centerPixel),
            cornerPixel: Array.from(cornerPixel)
        }});
    }} catch (e) {{
        document.getElementById('result').innerText = JSON.stringify({{ error: e.toString() }});
    }}
}});
</script></body></html>
"""
        test_html = Path("tools/temp_ps_exec_test.html")
        test_html.write_text(html_content, encoding="utf-8")

        try:
            cmd = [
                str(self.chrome_path),
                "--headless=new",
                "--disable-gpu-sandbox",
                "--use-gl=angle",
                "--dump-dom",
                f"file:///{test_html.resolve().as_posix()}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
            self.assertIsNotNone(match, f"No result in DOM: {res.stdout[:400]}")
            result = json.loads(match.group(1))

            self.assertTrue(result.get("success"), f"WebGL2 PS draw failed: {result.get('error')}")
            center = result["centerPixel"]
            corner = result["cornerPixel"]

            # Assert exact match with CPU calculation
            for ch in range(4):
                diff = abs(center[ch] - exp_pixel[ch])
                self.assertLessEqual(
                    diff, 1,
                    f"Pixel mismatch at channel {ch}: GPU {center[ch]} vs CPU {exp_pixel[ch]}"
                )

            # Outside triangle retains clear color RGBA(0, 0, 0, 255)
            self.assertEqual(corner, [0, 0, 0, 255])
        finally:
            if test_html.exists():
                test_html.unlink()

    def test_webgl2_alpha_blending_verification(self):
        """Verify WebGL2 alpha blending using ps_2_0 computed opacity output."""
        if not self.chrome_path.exists():
            self.skipTest(f"Chrome not found at {self.chrome_path}")

        vs_glsl, _ = translate_d3d9_to_glsl(self.vs20.bytecode, "glsl120")
        vs_es3 = adapt_vs_paired(vs_glsl)

        ps_glsl, _ = translate_d3d9_to_glsl(self.ps20_std.bytecode, "glsl120")
        ps_es3 = adapt_to_glsl_es_300(ps_glsl, stage="fragment")

        diffuse_texels = [204, 102, 51, 204] * 4
        opacity_texels = [0, 0, 0, 128] * 4
        vert_color = [0.5, 0.8, 1.0, 1.0]

        # Destination background: RGBA(0.2, 0.3, 0.4, 1.0) -> [51, 76, 102, 255]
        dst_norm = [51 / 255.0, 76 / 255.0, 102 / 255.0, 1.0]

        diffuse_norm = [c / 255.0 for c in [204, 102, 51, 204]]
        opacity_norm = [c / 255.0 for c in [0, 0, 0, 128]]
        src_norm = simulate_d3d9_ps_2_0_standard(diffuse_norm, opacity_norm, vert_color)
        blended_norm = simulate_alpha_blend(src_norm, dst_norm)
        exp_blended_pixel = [round(c * 255.0) for c in blended_norm]

        tri_verts = [
            -0.5, -0.5, 0.5, 1.0,
             0.5, -0.5, 0.5, 1.0,
             0.0,  0.5, 0.5, 1.0,
        ]
        tri_tc0 = [0.5, 0.5, 0.0, 0.0] * 3
        tri_tc1 = [0.5, 0.5, 0.0, 0.0] * 3
        tri_colors = vert_color * 3

        matrix_flat = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        pos_fixup = [1.0, 1.0, 0.0, 0.0]

        html_content = f"""<!DOCTYPE html>
<html><body><pre id="result">WAIT</pre><script>
window.addEventListener('DOMContentLoaded', () => {{
    try {{
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const gl = canvas.getContext('webgl2');
        if (!gl) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'No WebGL2' }});
            return;
        }}

        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `{vs_es3}`);
        gl.compileShader(vs);

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `{ps_es3}`);
        gl.compileShader(fs);

        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);

        gl.useProgram(prog);

        const uMat = gl.getUniformLocation(prog, 'vs_uniforms_vec4[0]');
        gl.uniform4fv(uMat, new Float32Array({json.dumps(matrix_flat)}));

        const uFixup = gl.getUniformLocation(prog, 'posFixup');
        gl.uniform4fv(uFixup, new Float32Array({json.dumps(pos_fixup)}));

        const t0 = gl.createTexture();
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, t0);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 2, 2, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array({json.dumps(diffuse_texels)}));
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.uniform1i(gl.getUniformLocation(prog, 'ps_s0'), 0);

        const t1 = gl.createTexture();
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, t1);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 2, 2, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array({json.dumps(opacity_texels)}));
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.uniform1i(gl.getUniformLocation(prog, 'ps_s1'), 1);

        const vBuf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, vBuf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_verts)}), gl.STATIC_DRAW);
        const posLoc = gl.getAttribLocation(prog, 'vs_v0');
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 4, gl.FLOAT, false, 0, 0);

        const tc0Buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, tc0Buf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_tc0)}), gl.STATIC_DRAW);
        const tc0Loc = gl.getAttribLocation(prog, 'a_texcoord0');
        gl.enableVertexAttribArray(tc0Loc);
        gl.vertexAttribPointer(tc0Loc, 4, gl.FLOAT, false, 0, 0);

        const tc1Buf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, tc1Buf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_tc1)}), gl.STATIC_DRAW);
        const tc1Loc = gl.getAttribLocation(prog, 'a_texcoord1');
        gl.enableVertexAttribArray(tc1Loc);
        gl.vertexAttribPointer(tc1Loc, 4, gl.FLOAT, false, 0, 0);

        const colBuf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, colBuf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_colors)}), gl.STATIC_DRAW);
        const colLoc = gl.getAttribLocation(prog, 'a_color');
        gl.enableVertexAttribArray(colLoc);
        gl.vertexAttribPointer(colLoc, 4, gl.FLOAT, false, 0, 0);

        gl.viewport(0, 0, 64, 64);
        gl.clearColor(51.0/255.0, 76.0/255.0, 102.0/255.0, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        // Enable alpha blending
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        gl.drawArrays(gl.TRIANGLES, 0, 3);

        const centerPixel = new Uint8Array(4);
        gl.readPixels(32, 32, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, centerPixel);

        document.getElementById('result').innerText = JSON.stringify({{
            success: true,
            centerPixel: Array.from(centerPixel)
        }});
    }} catch (e) {{
        document.getElementById('result').innerText = JSON.stringify({{ error: e.toString() }});
    }}
}});
</script></body></html>
"""
        test_html = Path("tools/temp_blend_test.html")
        test_html.write_text(html_content, encoding="utf-8")

        try:
            cmd = [
                str(self.chrome_path),
                "--headless=new",
                "--disable-gpu-sandbox",
                "--use-gl=angle",
                "--dump-dom",
                f"file:///{test_html.resolve().as_posix()}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
            self.assertIsNotNone(match, f"No result in DOM: {res.stdout[:400]}")
            result = json.loads(match.group(1))

            self.assertTrue(result.get("success"), f"Blending draw failed: {result.get('error')}")
            center = result["centerPixel"]

            # Channel-by-channel comparison within rounding threshold (+-1)
            for ch in range(4):
                diff = abs(center[ch] - exp_blended_pixel[ch])
                self.assertLessEqual(
                    diff, 1,
                    f"Blending mismatch at channel {ch}: GPU {center[ch]} vs CPU {exp_blended_pixel[ch]}"
                )
        finally:
            if test_html.exists():
                test_html.unlink()

    def test_authentic_standard_shader_pair_validation(self):
        """Validate genuine standard shader pair (vs_1_1 at 0x0bc0 + ps_2_0 at 0x0a68) in WebGL2.

        Zero synthetic varyings or artificial overrides are used.
        The vertex shader natively outputs:
          - gl_Position (from WVP dot products)
          - vFrontColor (from v1 * (2, 2, 2, 1) overbright modulation)
          - vTexCoord0  (from v2 + cvTextureOffset)
          - vTexCoord1  (from v3 opacity UV)
        The pixel shader natively consumes vFrontColor, vTexCoord0, vTexCoord1.
        """
        if not self.chrome_path.exists():
            self.skipTest(f"Chrome not found at {self.chrome_path}")

        # 1. Translate authentic vs_1_1 and ps_2_0 bytecodes without synthetic injection
        vs_glsl, vs_err = translate_d3d9_to_glsl(self.vs11.bytecode, "glsl120")
        self.assertEqual(vs_err, 0)
        ps_glsl, ps_err = translate_d3d9_to_glsl(self.ps20_std.bytecode, "glsl120")
        self.assertEqual(ps_err, 0)

        # 2. Strict GLSL ES 3.00 syntax adaptation only
        vs_es3 = adapt_to_glsl_es_300(vs_glsl, stage="vertex")
        ps_es3 = adapt_to_glsl_es_300(ps_glsl, stage="fragment")

        # Verify no synthetic varyings were added to source
        self.assertNotIn("a_texcoord0", vs_es3)
        self.assertNotIn("a_texcoord1", vs_es3)
        self.assertNotIn("a_color", vs_es3)

        # 3. Known inputs
        # Matrix c0..c3: Identity
        c0 = [1.0, 0.0, 0.0, 0.0]
        c1 = [0.0, 1.0, 0.0, 0.0]
        c2 = [0.0, 0.0, 1.0, 0.0]
        c3 = [0.0, 0.0, 0.0, 1.0]
        # c4: cvTextureOffset
        c4 = [0.25, 0.5, 0.0, 0.0]
        matrix_uniforms = c0 + c1 + c2 + c3 + c4
        pos_fixup = [1.0, 1.0, 0.0, 0.0]

        # Geometry: Triangle in NDC
        tri_v0 = [
            -0.5, -0.5, 0.5, 1.0,
             0.5, -0.5, 0.5, 1.0,
             0.0,  0.5, 0.5, 1.0,
        ]
        # v1: Vertex color RGBA(0.25, 0.4, 0.5, 0.8)
        vert_color = [0.25, 0.4, 0.5, 0.8]
        tri_v1 = vert_color * 3

        # v2: Diffuse UVs (0.1, 0.2, 0.0, 0.0) -> offset by c4 to (0.35, 0.7)
        diff_uv = [0.1, 0.2, 0.0, 0.0]
        tri_v2 = diff_uv * 3

        # v3: Opacity UVs (0.6, 0.8, 0.0, 0.0)
        opac_uv = [0.6, 0.8, 0.0, 0.0]
        tri_v3 = opac_uv * 3

        # Textures:
        # Diffuse (s0): RGBA(200, 150, 100, 220)
        diffuse_texels = [200, 150, 100, 220] * 4
        # Opacity (s1): RGBA(0, 0, 0, 180)
        opacity_texels = [0, 0, 0, 180] * 4

        # 4. CPU Reference Calculation
        # VS instruction: mul oD0, v1, c5.xxxy where c5 = (2.0, 1.0, 0.0, 0.0)
        v_front_color = [
            vert_color[0] * 2.0,
            vert_color[1] * 2.0,
            vert_color[2] * 2.0,
            vert_color[3] * 1.0,
        ]
        diff_norm = [c / 255.0 for c in [200, 150, 100, 220]]
        opac_norm = [c / 255.0 for c in [0, 0, 0, 180]]

        # PS instructions:
        # r0 = opacity sample
        # r1 = diffuse sample
        # r1.w = opacity.a * diffuse.a
        # r0 = r1 * vFrontColor
        exp_r = diff_norm[0] * v_front_color[0]
        exp_g = diff_norm[1] * v_front_color[1]
        exp_b = diff_norm[2] * v_front_color[2]
        exp_a = (diff_norm[3] * opac_norm[3]) * v_front_color[3]
        exp_pixel = [round(exp_r * 255.0), round(exp_g * 255.0), round(exp_b * 255.0), round(exp_a * 255.0)]

        # 5. Execute in WebGL2 headless Chrome
        html_content = f"""<!DOCTYPE html>
<html><body><pre id="result">WAIT</pre><script>
window.addEventListener('DOMContentLoaded', () => {{
    try {{
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const gl = canvas.getContext('webgl2');
        if (!gl) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'No WebGL2' }});
            return;
        }}

        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `{vs_es3}`);
        gl.compileShader(vs);
        if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'VS: ' + gl.getShaderInfoLog(vs) }});
            return;
        }}

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `{ps_es3}`);
        gl.compileShader(fs);
        if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'FS: ' + gl.getShaderInfoLog(fs) }});
            return;
        }}

        const prog = gl.createProgram();
        gl.attachShader(prog, vs);
        gl.attachShader(prog, fs);
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {{
            document.getElementById('result').innerText = JSON.stringify({{ error: 'Link: ' + gl.getProgramInfoLog(prog) }});
            return;
        }}

        gl.useProgram(prog);

        const uMat = gl.getUniformLocation(prog, 'vs_uniforms_vec4[0]');
        gl.uniform4fv(uMat, new Float32Array({json.dumps(matrix_uniforms)}));

        const uFixup = gl.getUniformLocation(prog, 'posFixup');
        gl.uniform4fv(uFixup, new Float32Array({json.dumps(pos_fixup)}));

        const t0 = gl.createTexture();
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, t0);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 2, 2, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array({json.dumps(diffuse_texels)}));
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.uniform1i(gl.getUniformLocation(prog, 'ps_s0'), 0);

        const t1 = gl.createTexture();
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, t1);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 2, 2, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array({json.dumps(opacity_texels)}));
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.uniform1i(gl.getUniformLocation(prog, 'ps_s1'), 1);

        const b0 = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, b0);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_v0)}), gl.STATIC_DRAW);
        const l0 = gl.getAttribLocation(prog, 'vs_v0');
        gl.enableVertexAttribArray(l0);
        gl.vertexAttribPointer(l0, 4, gl.FLOAT, false, 0, 0);

        const b1 = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, b1);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_v1)}), gl.STATIC_DRAW);
        const l1 = gl.getAttribLocation(prog, 'vs_v1');
        gl.enableVertexAttribArray(l1);
        gl.vertexAttribPointer(l1, 4, gl.FLOAT, false, 0, 0);

        const b2 = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, b2);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_v2)}), gl.STATIC_DRAW);
        const l2 = gl.getAttribLocation(prog, 'vs_v2');
        gl.enableVertexAttribArray(l2);
        gl.vertexAttribPointer(l2, 4, gl.FLOAT, false, 0, 0);

        const b3 = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, b3);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array({json.dumps(tri_v3)}), gl.STATIC_DRAW);
        const l3 = gl.getAttribLocation(prog, 'vs_v3');
        gl.enableVertexAttribArray(l3);
        gl.vertexAttribPointer(l3, 4, gl.FLOAT, false, 0, 0);

        gl.viewport(0, 0, 64, 64);
        gl.clearColor(0.0, 0.0, 0.0, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        gl.drawArrays(gl.TRIANGLES, 0, 3);

        const centerPixel = new Uint8Array(4);
        gl.readPixels(32, 32, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, centerPixel);

        const cornerPixel = new Uint8Array(4);
        gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, cornerPixel);

        document.getElementById('result').innerText = JSON.stringify({{
            success: true,
            centerPixel: Array.from(centerPixel),
            cornerPixel: Array.from(cornerPixel)
        }});
    }} catch (e) {{
        document.getElementById('result').innerText = JSON.stringify({{ error: e.toString() }});
    }}
}});
</script></body></html>
"""
        test_html = Path("tools/temp_authentic_std_pair.html")
        test_html.write_text(html_content, encoding="utf-8")

        try:
            cmd = [
                str(self.chrome_path),
                "--headless=new",
                "--disable-gpu-sandbox",
                "--use-gl=angle",
                "--dump-dom",
                f"file:///{test_html.resolve().as_posix()}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
            self.assertIsNotNone(match, f"No result in DOM: {res.stdout[:400]}")
            result = json.loads(match.group(1))

            self.assertTrue(result.get("success"), f"Authentic shader pair rendering failed: {result.get('error')}")
            center = result["centerPixel"]
            corner = result["cornerPixel"]

            # Channel-by-channel comparison within rounding threshold (+-1)
            for ch in range(4):
                diff = abs(center[ch] - exp_pixel[ch])
                self.assertLessEqual(
                    diff, 1,
                    f"Pixel channel {ch} mismatch: GPU {center[ch]} vs CPU {exp_pixel[ch]}"
                )

            # Outside triangle retains background clear color
            self.assertEqual(corner, [0, 0, 0, 255])
        finally:
            if test_html.exists():
                test_html.unlink()

    def test_malformed_pixel_shader_bytecode_rejection(self):
        """Verify that malformed pixel shader bytecodes are rejected by MojoShader with error count > 0."""
        # Corrupt pixel shader header with invalid token length
        corrupt_ps = b"\xff\xff\x02\x00" + b"\x00\x00\x00\x00" * 4
        glsl_src, err_count = translate_d3d9_to_glsl(corrupt_ps, "glsl120")
        self.assertGreater(err_count, 0)
        self.assertEqual(glsl_src, "")


if __name__ == "__main__":
    unittest.main()
