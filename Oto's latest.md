# PortSpeed — Engineering Handoff & Architecture Status

**Document:** `Oto's latest.md`<br>
**Date:** November 1, 2026<br>
**Repository:** `https://github.com/OtariTB/PortSpeed.git` (branch `main`)<br>
**Target:** PC v1.1 `nfs.exe` (SHA-256: `66d0ef062b8cf145941656f71d5300ee7a18413eb44747c0c1b72e5927ad7404`)

---

## 1. Project Overview

### 1.1 Objective
**PortSpeed** is an engineering effort to statically recompile the authentic 32-bit x86 Windows executable of *Need for Speed: ProStreet* (PC v1.1) to run natively in modern web browsers via WebAssembly and browser graphics APIs (WebGL2 / WebGPU). Rather than using slow instruction emulation or rewriting the proprietary game engine from scratch, PortSpeed translates the original lifted x86 machine instructions into portable, standard C99 code, links it against a custom Win32/CRT/Direct3D compatibility layer, and serializes graphics commands to a browser-side WebGL2 consumer.

### 1.2 Core Architecture
The system is divided into four primary layers:
1. **1:1 Guest Linear Memory Space (`0x00000000..0x28000000`)**:
   - `0x00000000..0x00100000`: Null-page guard.
   - `0x00100000..0x00200000`: Thread Environment Block (TEB) & Thread Local Storage (TLS).
   - `0x00200000..0x00400000`: 2 MB Guest stack (`ESP` initialized to `0x003FF000`).
   - `0x00401000..0x00967000`: Authentic `.text` segment.
   - `0x00967000..0x00a4a000`: Authentic `.rdata` segment (vtables, strings, IAT, initializer tables).
   - `0x00a4a000..0x01010000`: Authentic `.data` segment (global variables, BSS).
   - `0x01010000..0x01011000`: `.tls` template.
   - `0x01011000..0x010ea000`: `.rsrc` segment (containing 34 compiled D3DX9 `.fx` shader effects).
   - `0x02000000..0x28000000`: Dynamic guest heap (up to 640 MB).
2. **Master Dispatch Table (`g_dtab`)**:
   - Direct $O(1)$ function pointer array of 5,660,672 entries covering `0x00401000..0x00967000`.
   - Dispatches lifted functions and imported IAT shims with zero hash map lookup overhead.
3. **C99 Platform Shims**:
   - **CRT (`MSVCR80.dll`)**: 156 shims covering memory allocation, string operations, math, FPU control, and C++ static initialization.
   - **Win32 (`KERNEL32.dll`, `USER32.dll`, `ADVAPI32.dll`)**: 198 shims for synchronization (critical sections, mutexes, semaphores), registry queries, timing (QPC, `GetTickCount`), window messaging, and TLS allocation.
   - **Direct3D 9 COM Shim**: Implements `Direct3DCreate9` and `IDirect3DDevice9` vtables in C99, serializing D3D9 API calls into a lockless shared-memory ring buffer.
4. **Browser WebGL2 Command Consumer (`web/src/d3d9_consumer.ts`)**:
   - Reads the shared-memory command ring buffer packet stream.
   - Converts D3D9 viewport coordinates, manages D3D9 render states, and executes corresponding WebGL2 draw/clear commands.

### 1.3 Key Source Code Locations
- [`runtime/`](file:///c:/Users/tabat/OneDrive/Desktop/NFS-PortStreet-Project/runtime/):
  - `memory.h`, `memory.c`: 1:1 guest memory management and virtual allocation.
  - `cpu.h`: x86 register context, SIMD128 vector math, and x87 80-bit FPU circular stack.
  - `crt.h`, `crt.c`: MSVCR80 IAT shim implementations.
  - `win32.h`, `win32.c`: Win32 subsystem shims.
  - `initterm.h`, `initterm.c`: Static initializer table execution and atexit handling.
  - `boot.h`, `boot.c`: ProStreet `main()` entry, stack frame construction, and boot orchestration.
  - `d3d9.h`, `d3d9.c`: Direct3D9 COM vtables and device emulation.
  - `d3d9_cmd.h`: Binary packet definitions for the D3D9 command ring buffer protocol.
- [`web/src/`](file:///c:/Users/tabat/OneDrive/Desktop/NFS-PortStreet-Project/web/src/):
  - `d3d9_consumer.ts`: TypeScript WebGL2 command consumer.
- [`tools/`](file:///c:/Users/tabat/OneDrive/Desktop/NFS-PortStreet-Project/tools/):
  - `d3dx9_effect.py`: Read-only parser for compiled D3DX9 effect files (`.fx`).
  - `guest_boot.py`: End-to-end Python simulator for the guest boot chain.
  - `guest_d3d9.py`: Simulation and validation harness for D3D9 device initialization.
  - `lift_d3d9.py`: Extractor for genuine graphics initialization functions.
  - `d3d9_consumer.bundle.js`: Pre-bundled IIFE build of the TypeScript consumer for test runners.
- [`tests/`](file:///c:/Users/tabat/OneDrive/Desktop/NFS-PortStreet-Project/tests/):
  - 225 automated unit, integration, and headless Chrome WebGL2 tests.

---

## 2. Progress by Phase

### Phase 1: SecuROM Deobfuscation & Master Catalog [COMPLETED]
- **Neutralized SecuROM Stubs**: 220 countdown obfuscation stubs nopped.
- **Symbolic Trampoline Resolution**: 2,153 indirect jump sites resolved via Unicorn Engine 2.1.4 and Capstone disassembler.
- **Control-Flow Recovery**: 31,995 functions and 220,816 basic blocks cataloged across authentic binary code space.

### Phase 2: Static x86-to-C99 Lifter [COMPLETED]
- **SIMD / SSE Support**: Full SSE/SSE2 instruction support mapped to WebAssembly SIMD128 (`v128_t`) intrinsics.
- **x87 FPU Emulation**: Full 80-bit precision, 8-level circular register stack (`st[8]`), FCW, and FSW flags.
- **Zero-Latency Arithmetic Flags**: Bit-parallel flag computation (`FLAGS_ADC_M`, `FLAGS_SBB_M`, `FLAGS_LOG_M`).
- **32-Shard Modular Pipeline**: Sharded into 32 clean C99 modules (`shard_00.c` .. `shard_31.c`) with direct `g_dtab` function dispatch.

### Phase 3: Platform Runtime & Engine Boot Chain [COMPLETED]
- **Linear Memory & TEB/TLS**: Validated memory mapping with TEB and TLS segment at `0x00100000`.
- **CRT & Win32 Shims**: 156 MSVCR80 shims and 198 Win32 shims verified against genuine IAT layouts.
- **Static C++ Initializers (`_initterm`)**: Executed all 960 global constructors in the binary initializer table, hooked the `sub_0082851b` atexit handler.
- **Boot Orchestration**: Validated ProStreet `main()` entry, stack layout, argument parsing (`-safemode`), and clean dry-run lifecycle.

### Phase 4.1: Direct3D9 COM Compatibility & Command Ring Buffer [COMPLETED]
- **D3D9 COM Interfaces**: Implemented `Direct3DCreate9` and `IDirect3DDevice9` vtables in C99.
- **Command Ring Buffer (`d3d9_cmd.h`)**: Defined lockless shared-memory ring buffer with 32-byte header, 8-byte aligned packets, and wraparound handling.
- **Lifted Function Execution**: Verified genuine lifted graphics initialization routines:
  - `sub_0070e150`: D3D9 device creation and initialization.
  - `sub_00705d30`: Scene rendering loop producing genuine `BeginScene`, `Clear`, `EndScene`, and `Present` packets.

### Phase 4.2: D3DX9 Effect Parsing & MojoShader Translation [COMPLETED]
- **Parser Implementation (`tools/d3dx9_effect.py`)**: Built a read-only binary parser for compiled D3DX9 effect resources (`FXv1` format).
- **All 34 Embedded Effects Validated**: Cataloged parameters, techniques, passes, sampler bindings, and 597 embedded shader bytecodes across `.rsrc`.
- **MojoShader Translation Pipeline**: Integrated MojoShader 1.0 to translate authentic D3D9 bytecode to GLSL ES 3.00 for WebGL2.
- **Authenticity Audit**: Discovered and verified that `IDI_STANDARD_FX` `standard::p0` pairs vertex shader `vs_1_1` (offset `0x0bc0`) with pixel shader `ps_2_0` (offset `0x0a68`).
- **WebGL2 Shader Validation**: Compiled, linked, and rendered the authentic shader pair in headless Chrome WebGL2 using diagnostic textures and geometry.

### Phase 4.3: WebGL2 Command Consumer & Render States [IN PROGRESS]
- **TypeScript Consumer (`web/src/d3d9_consumer.ts`)**: Implemented browser-side consumer processing ring buffer packets.
- **Supported Commands**:
  - `D3DCMD_BEGIN_SCENE`, `D3DCMD_END_SCENE`: Strict state machine validation.
  - `D3DCMD_CLEAR`: Clears color, depth, and stencil with sub-viewport scissor clamping.
  - `D3DCMD_PRESENT`: Tracks frame count and triggers canvas presentation.
  - `D3DCMD_SET_VIEWPORT`: Converts D3D9 coordinates (top-left origin, $[0, 1]$ depth) to WebGL2 (bottom-left origin, $[0, 1]$ depth via `gl.depthRangef`).
  - `D3DCMD_SET_RENDER_STATE`: Supports 8 critical states:
    - `D3DRS_ZENABLE` (`gl.DEPTH_TEST`)
    - `D3DRS_ZWRITEENABLE` (`gl.depthMask`)
    - `D3DRS_ZFUNC` (`gl.depthFunc`)
    - `D3DRS_CULLMODE` (`gl.CULL_FACE`, front-face CW, culling CW/CCW)
    - `D3DRS_ALPHABLENDENABLE` (`gl.BLEND`)
    - `D3DRS_SRCBLEND`, `D3DRS_DESTBLEND` (`gl.blendFunc`)
    - `D3DRS_COLORWRITEENABLE` (`gl.colorMask`)
- **Direct3D 9 Clear Compatibility Correction**:
  - *Specification Correction*: Per Microsoft Direct3D 9 documentation, `IDirect3DDevice9::Clear` is **not** affected by `D3DRS_COLORWRITEENABLE`, `D3DRS_ZWRITEENABLE`, or stencil write masks.
  - *Consumer Behavior*: During `CLEAR`, the consumer temporarily overrides `gl.colorMask(true, true, true, true)`, `gl.depthMask(true)`, and `gl.stencilMask(0xFFFFFFFF)`, and restores active render-state masks immediately after clear.
  - *Verification*: Verified in real WebGL2 that clear operations unconditionally affect all channels, while subsequent geometry draws strictly obey the active masks.

> [!IMPORTANT]
> **Authenticity Note**: Tested infrastructure must not be confused with full game execution. The project has verified the runtime environment, CRT/Win32 shims, static initializer chains, lifted graphics init functions, and WebGL2 command processing in isolation. The complete game does not yet boot to a playable 3D scene.

---

## 3. Latest Verified State

- **Automated Test Suite**:
  - Python unittest regression suite: **225 tests passing (100% green, 12 skipped, 0 failures)**.
  - TypeScript node test suite: **11 unit tests passing (100% green, 0 failures)**.
- **Headless Chrome WebGL2 Integration**:
  - Verified genuine ProStreet graphics initialization functions (`sub_0070e150`, `sub_00705d30`) write command streams that the WebGL2 consumer parses and renders cleanly.
  - Verified `CLEAR` color readback, circular buffer wraparound, viewport calculation, and 8 render states.
  - Verified that `Clear` temporarily overrides write masks and restores active masks for subsequent draw operations.
  - WebGL2 shader tests currently execute with diagnostic geometry (triangle/quad) and test textures rather than full game models.

---

## 4. Current Limitations & Known Blockers

1. **Draw Calls & Buffers Not Connected**:
   - The D3D9 command consumer handles `BEGIN_SCENE`, `END_SCENE`, `CLEAR`, `PRESENT`, `SET_VIEWPORT`, and `SET_RENDER_STATE`.
   - Vertex buffer (`D3DCMD_CREATE_VERTEX_BUFFER`, `D3DCMD_SET_STREAM_SOURCE`), index buffer, vertex declaration, and draw primitive packets are not yet implemented in the consumer.
2. **Dynamic Shader Pipeline**:
   - MojoShader transpilation has been validated offline via Python test harnesses. A dynamic runtime mechanism (compiling shaders as the game binds them or pre-transpiling all 597 shaders into a lookup table) is pending.
3. **Texture Lifecycle**:
   - Texture creation, format conversion (e.g., BC1/BC2/BC3 DXT to WebGL2 compressed formats), and sampler state bindings are not yet connected to the browser command stream.
4. **Input, Audio & Storage**:
   - DirectInput8 keyboard/gamepad shims are not yet implemented.
   - DirectSound / AudioWorklet pipeline is not yet implemented.
   - Asset streaming from original `.big` / `.bun` archives (OPFS chunk-based streaming) is not yet active.
5. **Original Executable Stability**:
   - Full gameplay execution requires completing Phase 4 (graphics stream) before the game's main simulation tick can run without blocking on rendering resources.

---

## 5. Next Recommended Milestone

### Phase 4.3 — Vertex Buffer Resource Lifecycle & Stream Binding

The immediate next step is to enable vertex buffer allocation, data uploading, and stream binding in the D3D9 command consumer.

#### Planned Scope:
1. **Command Packet Definitions (`runtime/d3d9_cmd.h`)**:
   - Review existing packet IDs to prevent opcode collisions.
   - Define:
     - `D3DCMD_CREATE_VERTEX_BUFFER`: Buffer ID, byte size, usage flags, FVF / declaration format.
     - `D3DCMD_UPDATE_VERTEX_BUFFER`: Buffer ID, byte offset, byte length, followed by vertex data payload.
     - `D3DCMD_SET_STREAM_SOURCE`: Stream number, Buffer ID, offset in bytes, stride in bytes.
     - `D3DCMD_DESTROY_VERTEX_BUFFER`: Buffer ID for cleanup.
2. **WebGL2 Consumer Handlers (`web/src/d3d9_consumer.ts`)**:
   - Maintain a map of active `WebGLBuffer` handles keyed by buffer ID.
   - Handle buffer allocation (`gl.createBuffer()`, `gl.bufferData()`).
   - Handle sub-data upload (`gl.bufferSubData()`).
   - Track bound stream sources per stream slot.
   - Handle buffer destruction (`gl.deleteBuffer()`).
3. **Automated Verification**:
   - Add unit tests in `web/tests/d3d9_consumer.test.ts` for buffer lifecycle and stream state.
   - Add headless Chrome WebGL2 tests in `tests/test_d3d9_consumer.py` verifying vertex data readback via transform feedback or diagnostic draw.
   - Run the full 225+ test regression suite.

*(Note: This is the recommended next task. Do not implement it until authorized.)*

---

## 6. How to Resume Development

### 6.1 Prerequisites & Environment Setup
- **OS**: Windows 10/11 x64.
- **Python**: 3.10+ with `capstone`, `unicorn` (v2.1.4), `pefile`.
- **Node.js**: v18+ with `npm`.
- **Google Chrome**: Installed at `C:\Program Files\Google\Chrome\Application\chrome.exe` (used for headless WebGL2 integration tests via `--headless=new --use-gl=angle`).
- **Clang / clangd**: LLVM 17+ or VS Code clangd extension for runtime header diagnostics.

### 6.2 Working with the Original Game Files
- **Strictly Read-Only**: The original game installation (`C:\Games\Pro Street\Need For Spped - Pro Street`) is **strictly read-only**. Never write to, modify, patch, or extract into that directory.
- All extracted test artifacts and reports are saved strictly in `research/local/` or managed via `.gitignore`.

### 6.3 Building & Running Tests

```powershell
# 1. Run the complete Python test suite (225 tests)
python -m unittest discover -s tests -v

# 2. Run the TypeScript D3D9 consumer test suite (11 tests)
npx tsx web/tests/d3d9_consumer.test.ts

# 3. Rebuild the consumer bundle if web/src/d3d9_consumer.ts is modified
npx esbuild web/src/d3d9_consumer.ts --bundle --format=iife --global-name=D3D9 --outfile=tools/d3d9_consumer.bundle.js

# 4. Verify runtime C99 header diagnostics (must report 0 errors)
python -c "
import os, subprocess
clangd = r'c:\Users\Giorgi\AppData\Roaming\Antigravity IDE\User\globalStorage\llvm-vs-code-extensions.vscode-clangd\install\23.1.0\clangd_23.1.0\bin\clangd.exe'
for f in sorted(os.listdir('runtime')):
    if f.endswith(('.c', '.h')):
        res = subprocess.run([clangd, f'--check=runtime/{f}'], capture_output=True, text=True)
        errs = [l for l in res.stderr.splitlines() if l.startswith('E[') and 'tweak' not in l]
        print(f'{f:15}: {\"CLEAN (0 errors)\" if not errs else f\"ERRORS: {errs}\"}')
"
```

### 6.4 Git Discipline
- **Local Commits Only**: All work is tracked on branch `main`.
- **Never push without explicit permission**: Follow the instructions in [`AGENTS.md`](file:///c:/Users/tabat/OneDrive/Desktop/NFS-PortStreet-Project/AGENTS.md).
- **Zero Errors Policy**: Any modifications to `runtime/` must maintain 0 errors under `clangd`.
