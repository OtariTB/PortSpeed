"""Test MojoShader translation and WebGL2 compilation using headless Chrome."""

import json
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from tools.build_win32_shims import EXE_PATH
from tools.inventory_effects import parse_pe_resources
from tools.d3dx9_effect import D3DX9EffectParser


def translate_d3d9_to_glsl(sh_bytes: bytes, profile: str = "glsl120") -> str:
    """Translate D3D9 shader bytecode using MojoShader native library."""
    import ctypes

    dll_path = Path("tools/lib/mojoshader.dll")
    if not dll_path.exists():
        raise FileNotFoundError(f"mojoshader.dll not found at {dll_path}")

    dll = ctypes.CDLL(str(dll_path.resolve()))

    class MOJOSHADER_parseData(ctypes.Structure):
        _fields_ = [
            ('error_count', ctypes.c_int),
            ('errors', ctypes.c_void_p),
            ('profile', ctypes.c_char_p),
            ('output', ctypes.c_char_p),
            ('output_len', ctypes.c_int),
            ('instruction_count', ctypes.c_int),
        ]

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
        raise RuntimeError(f"MOJOSHADER_parse failed with {pdata.error_count} errors")

    return pdata.output.decode('latin1')


def adapt_to_glsl_es_300(glsl120_source: str) -> str:
    """Adapt MojoShader GLSL 1.20 output into GLSL ES 3.00 for WebGL2."""
    lines = glsl120_source.strip().splitlines()
    out_lines = [
        "#version 300 es",
        "precision highp float;",
        "precision mediump int;",
    ]

    for line in lines:
        s = line.strip()
        if s.startswith("#version"):
            continue
        # Convert vertex input attributes to 'in'
        elif s.startswith("attribute "):
            out_lines.append(line.replace("attribute ", "in "))
        # Convert vertex varyings to 'out'
        elif s.startswith("varying "):
            out_lines.append(line.replace("varying ", "out "))
        else:
            out_lines.append(line)

    return "\n".join(out_lines) + "\n"


def run_webgl2_compilation_test(vs_source_glsl_es3: str):
    """Compile translated shader in headless Chrome WebGL2 context."""
    html_template = f"""<!DOCTYPE html>
<html>
<head><title>WebGL2 Shader Compile Test</title></head>
<body>
<pre id="result">RUNNING</pre>
<script>
window.addEventListener('DOMContentLoaded', () => {{
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const gl = canvas.getContext('webgl2');
    if (!gl) {{
        document.getElementById('result').innerText = JSON.stringify({{
            success: false,
            error: 'WebGL2 context not supported'
        }});
        return;
    }}

    const vsSource = `{vs_source_glsl_es3}`;

    const shader = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(shader, vsSource);
    gl.compileShader(shader);

    const compiled = gl.getShaderParameter(shader, gl.COMPILE_STATUS);
    const infoLog = gl.getShaderInfoLog(shader);

    // Complementary fragment shader to link a complete WebGL2 program
    const fsSource = `#version 300 es
precision mediump float;
in vec4 vTexCoord0;
out vec4 fragColor;
void main() {{
    fragColor = vTexCoord0;
}}
`;
    const fShader = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fShader, fsSource);
    gl.compileShader(fShader);

    const program = gl.createProgram();
    gl.attachShader(program, shader);
    gl.attachShader(program, fShader);
    gl.linkProgram(program);
    const linked = gl.getProgramParameter(program, gl.LINK_STATUS);
    const programLog = gl.getProgramInfoLog(program);

    // Active attributes reflection
    const activeAttribs = [];
    const numAttribs = gl.getProgramParameter(program, gl.ACTIVE_ATTRIBUTES);
    for (let i = 0; i < numAttribs; i++) {{
        const info = gl.getActiveAttrib(program, i);
        activeAttribs.push({{ name: info.name, size: info.size, type: info.type }});
    }}

    // Active uniforms reflection
    const activeUniforms = [];
    const numUniforms = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < numUniforms; i++) {{
        const info = gl.getActiveUniform(program, i);
        activeUniforms.push({{ name: info.name, size: info.size, type: info.type }});
    }}

    const result = {{
        success: compiled && linked,
        compiled: compiled,
        linked: linked,
        infoLog: infoLog,
        programLog: programLog,
        renderer: gl.getParameter(gl.RENDERER),
        version: gl.getParameter(gl.VERSION),
        shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
        activeAttribs: activeAttribs,
        activeUniforms: activeUniforms
    }};

    document.getElementById('result').innerText = JSON.stringify(result);
}});
</script>
</body>
</html>
"""
    test_html = Path('tools/test_shader.html')
    test_html.write_text(html_template, encoding='utf-8')

    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    cmd = [
        chrome_path,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--use-gl=angle',
        '--dump-dom',
        f'file:///{test_html.resolve().as_posix()}'
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    match = re.search(r'<pre id="result">(.*?)</pre>', res.stdout, re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not extract result from DOM:\n{res.stdout[:500]}")

    return json.loads(match.group(1))


def main():
    data = EXE_PATH.read_bytes()
    entries = parse_pe_resources(data)
    entry = [e for e in entries if e[0] == 'IDI_STANDARD_FX'][0]
    fx = data[entry[3] : entry[3] + entry[1]]

    parser = D3DX9EffectParser(fx)
    effect = parser.parse()
    vs20 = [s for s in effect.shaders if s.target == 'vs_2_0'][0]

    print(f"1. Selected vertex shader: {vs20.target} from IDI_STANDARD_FX ({vs20.length} bytes)")

    glsl_raw = translate_d3d9_to_glsl(vs20.bytecode, "glsl120")
    print("\n2. MojoShader translation output (GLSL 1.20):")
    print(glsl_raw.strip())

    glsl_es3 = adapt_to_glsl_es_300(glsl_raw)
    print("\n3. Adapted GLSL ES 3.00 shader:")
    print(glsl_es3.strip())

    print("\n4. Running headless Chrome WebGL2 compilation test...")
    result = run_webgl2_compilation_test(glsl_es3)

    print("\n=== WebGL2 COMPILATION RESULTS ===")
    print(f"Success: {result.get('success')}")
    print(f"Shader Compiled: {result.get('compiled')}")
    print(f"Program Linked: {result.get('linked')}")
    print(f"WebGL Renderer: {result.get('renderer')}")
    print(f"WebGL Version: {result.get('version')}")
    print(f"GLSL Version: {result.get('shadingLanguageVersion')}")
    print(f"Active Attributes: {result.get('activeAttribs')}")
    print(f"Active Uniforms: {result.get('activeUniforms')}")
    if result.get('infoLog'):
        print(f"Shader InfoLog: {result.get('infoLog')}")
    if result.get('programLog'):
        print(f"Program InfoLog: {result.get('programLog')}")


if __name__ == "__main__":
    main()
