# PortSpeed - AI Agent Guidelines & Engineering Rules

> **Project Target:** Native browser port of *Need for Speed: ProStreet* (PC v1.1, `nfs.exe`) using static x86 binary recompilation and WebAssembly.

---

## 1. Non-Negotiable Operational Rules

1. **STRICTLY NO GIT PUSH:**
   - **Never** execute `git push` under any circumstances unless the user gives an explicit, verbatim command to push. All commits and changes must remain strictly local.
2. **Read-Only Target Game Installation:**
   - The original game installation (`C:\Games\Pro Street\Need For Spped - Pro Street`) is **strictly read-only**.
   - Never write, edit, delete, patch, extract into, or change permissions in the game installation directory.
3. **Strict Step-by-Step Execution Discipline:**
   - **Never jump ahead across steps or phases autonomously.**
   - When assigned a specific step (e.g. Step 4.1), complete **only** that step, thoroughly verify it with automated tests and language-server checks, report the exact diffs and verification results to the user, and **wait for the user's explicit command** before touching the next step.
4. **Editor Diagnostics & Runtime Hygiene:**
   - All files in `runtime/` must maintain **0 errors** in the IDE (VS Code / Antigravity IDE language server `clangd` and MSVC IntelliSense).
   - Any new runtime headers must be self-contained and compatible with both native host and WebAssembly compilation targets (`__wasm__`).
   - Standard C headers are mapped via the clean C99 declarations in `include/` and configured in `.clangd` and `.vscode/c_cpp_properties.json`.
5. **No Proprietary Binary Redistribution:**
   - Never commit raw game executables, extracted game assets, or decompiled copyrighted code to git.
   - All analysis artifacts, generated files, and cached assets are strictly governed by `.gitignore`.

---

## 2. Architecture & Technical Foundation

- **Static Ahead-Of-Time (AOT) Recompilation:**
  - 31,995 recovered x86 functions cataloged across 220,816 basic blocks lifted into 32 modular C99 shards (`shard_00.c` .. `shard_31.c`).
  - Bit-parallel flag computation (`FLAGS_ADC_M`, `FLAGS_SBB_M`, `FLAGS_LOG_M`) for zero-latency branching.
  - Native WebAssembly SIMD128 (`v128_t`) intrinsics for vector math.
  - Full 80-bit precision x87 circular stack emulation (`st[8]`, FCW/FSW).
- **1:1 Guest Linear Memory Layout:**
  - `0x00000000..0x00100000`: Null-page guard.
  - `0x00100000..0x00200000`: Thread Environment Block (TEB) & TLS storage.
  - `0x00200000..0x00400000`: 2 MB Guest stack (`ESP` initialized to `0x003FF000`).
  - `0x00401000..0x00967000`: Authentic `.text` segment.
  - `0x00967000..0x00a4a000`: Authentic `.rdata` segment (vtables, strings, IAT, initializer tables).
  - `0x00a4a000..0x01010000`: Authentic `.data` segment (global variables, BSS).
  - `0x01010000..0x01011000`: `.tls` template.
  - `0x01011000..0x010ea000`: `.rsrc` (34 D3DX `.fx` shader effects).
  - `0x02000000..0x28000000`: Dynamic guest heap (up to 640 MB).
- **Master Dispatch Table (`g_dtab`):**
  - Direct $O(1)$ function pointer array of size 5,660,672 entries covering `0x00401000..0x00967000`.
  - Dispatches lifted functions and imported IAT shims with zero hash map overhead.

---

## 3. Master Plan & Completed Milestones

### Phase 1: SecuROM Deobfuscation & Master Catalog [COMPLETED]
- **Step 1.1: Automatic Nopping of Countdown Stubs** (220 genuine stubs neutralized).
- **Step 1.2: Symbolic Trampoline & Prologue Resolution** (100% of 2,153 indirect jump sites resolved via Unicorn Engine 2.1.4 and Capstone).
- **Step 1.3: Master Control-Flow Recovery** (31,995 functions, 220,816 basic blocks, 99.98% CFG recovery saved in `research/local/phase1/catalog.json`).

### Phase 2: Full-Scale Static x86-to-C99 Lifter [COMPLETED]
- **Step 2.1: Full SSE/SSE2 SIMD128 Instruction Support** (`runtime/cpu.h`, `xmm_reg_t`, `<wasm_simd128.h>`).
- **Step 2.2: Comprehensive x87 FPU Stack Emulation** (80-bit precision, 8-level circular stack, FCW/FSW).
- **Step 2.3: Arithmetic Flag Calculation & Fast Path Optimization** (Bit-parallel helpers).
- **Step 2.4: 32-Shard Output Pipeline & Master Dispatch Table** (`shard_00.c` .. `shard_31.c`, `g_dtab`).

### Phase 3: Platform Runtime & Engine Boot Chain [COMPLETED]
- **Step 3.1: 1:1 Linear Guest Memory Layout** (`runtime/memory.h`, `runtime/memory.c`).
- **Step 3.2: MSVCR80.dll IAT Shim Layer** (All 156 imports shimmed in C99, `runtime/crt.h`, `runtime/crt.c`).
- **Step 3.3: Win32 Core Emulation** (198 imports shimmed in C99, `runtime/win32.h`, `runtime/win32.c`).
- **Step 3.4: Static C++ Initializer Chain `_initterm`** (Executed all 960 constructors, hooked `sub_0082851b` atexit helper, `runtime/initterm.h`, `runtime/initterm.c`).
- **Step 3.5: ProStreet `main()` & Engine Boot Orchestration** (`runtime/boot.h`, `runtime/boot.c`, `tools/guest_boot.py`, boot state machine, argument parser, stack frame setup, clean dry-run lifecycle).

### Phase 4: Graphics Command Stream & WebGPU Renderer [NEXT / IN PROGRESS]
- **Step 4.1: Direct3D 9 COM Interface Shim** (`Direct3DCreate9` and `IDirect3DDevice9` vtable shims, draw call serialization to shared memory ring buffer).
- **Step 4.2: D3DX9 Effect (`ID3DXEffect`) Parser** (Translate 34 `.fx` shaders in `.rsrc` to WebGPU / WebGL2 bind groups).
- **Step 4.3: TypeScript Browser GPU Host** (Web Worker consumer, vertex buffer cache, BC texture decompression, 3D scene rendering).

### Phase 5: Audio, Input, Asset Streaming & Web Application Shell [PLANNED]
- **Step 5.1: DirectInput8 Keyboard, Gamepad & Touch Controls** (Browser SharedArrayBuffer input mapping + NFSU touch overlay).
- **Step 5.2: DirectSound AudioWorklet Pipeline** (PCM audio streams piped to AudioWorklet thread).
- **Step 5.3: OPFS Chunk-Based Asset Streaming** (Origin Private File System streaming worker for 5.6 GB game assets).
- **Step 5.4: Web Application Shell** (Responsive full-screen PWA interface).

### Phase 6: Racing Gameplay, Mobile Optimizations & Polish [PLANNED]
- **Step 6.1: Full Race Simulation & Physics Validation** (Havok physics integration, AI behavior, collision detection).
- **Step 6.2: Mobile Performance Presets** (Resolution scaling, ASTC 4x4 texture compression, mobile graphics tiers).

---

## 4. Development & Testing Commands

All commands are run from `PROSTREET/PortSpeed`:

```powershell
# Run the complete test suite (163 tests, 100% green)
python -m unittest discover -s tests -v

# Run engine boot simulation (validates memory layout, TEB, CRT, Win32, initterm, main)
python tools/guest_boot.py

# Check runtime language server diagnostics (must be 0 errors)
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
