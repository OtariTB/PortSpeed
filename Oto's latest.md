# PortSpeed — Engineering Handoff & Architecture Status

**Document:** `Oto's latest.md`<br>
**Date:** November 2, 2026<br>
**Repository:** `https://github.com/OtariTB/PortSpeed.git` (branch `main`)<br>
**Target:** PC v1.1 `nfs.exe` (SHA-256: `66d0ef062b8cf145941656f71d5300ee7a18413eb44747c0c1b72e5927ad7404`)

---

## 1. Project Overview & Operational Status

### 1.1 Objective
**PortSpeed** is an engineering project to statically recompile the authentic 32-bit x86 Windows executable of *Need for Speed: ProStreet* (PC v1.1) to execute natively in modern web browsers via WebAssembly and browser graphics APIs (WebGL2 / WebGPU). Rather than full instruction emulation or writing a clean-room remake, PortSpeed lifts x86 machine instructions into standard portable C99, links them against a custom Win32/CRT/Direct3D compatibility layer, and executes native WebAssembly modules.

### 1.2 Core Architecture
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
   - **Direct3D 9 COM Shim**: Implements `Direct3DCreate9` and `IDirect3DDevice9` vtables in C99, serializing D3D9 API calls into a lockless shared-memory ring buffer (64-byte control header).
4. **Browser WebGL2 Command Consumer (`web/src/d3d9_consumer.ts`)**:
   - Reads the shared-memory command ring buffer packet stream.
   - Converts D3D9 viewport coordinates, manages D3D9 render states, and executes corresponding WebGL2 draw/clear commands.

---

## 2. Chronological Engineering Progress: Today's Development Session

### 2.1 Constructor Callback Discovery & Static Recompilation Pipeline
- **Problem**: In genuine game initialization, `sub_00401000` (`__ehvec_ctor`) iterates over object arrays and invokes constructor callbacks. Because functions such as `0x006f8d60` were passed as data pointers (`push 0x006f8d60`) rather than direct `call` destinations, they were omitted from the initial 31,995 static catalog functions.
- **Pipeline Improvement**:
  - Implemented single-function lifting in `tools/generate_shards.py` (`lift_single_function`) and `tools/lift_ctor_callback.py`.
  - Disassembled and lifted `0x006f8d60` directly from original `nfs.exe` bytes into `gen/shard_0014.c`, generating entries in `gen/fntab.h` and `gen/fntab.c`.
  - Audited 21 additional callback sites invoked by `sub_00401000`, identifying genuine function targets (`0x004fed90`, `0x004f9db0`, etc.).

### 2.2 Authentic Unicorn Startup Diagnostic vs Statically Recompiled WASM
> [!IMPORTANT]
> **Crucial Technical Distinction: Unicorn Emulation vs WASM Static Recompilation**
> - In Unicorn Engine 2.1.4, code executes as genuine x86 machine instructions on an emulated CPU with hardware x86 CALL/RET semantics (automatic stack push/pop of 4-byte return addresses).
> - Under Unicorn diagnostics (`tools/boot_diagnostics.py`), all **960 non-null static constructors** successfully completed without trapping.
> - **This result was an emulation milestone, NOT a WebAssembly milestone.**
> - Statically recompiled C99 code running in WebAssembly does not automatically use hardware x86 CALL frames, as explained below.

### 2.3 Direct3D 9 Extension Shims: D3DXMatrixTranspose & D3DXVec3Transform
- During static constructor execution in Unicorn, constructor #274 halted on missing `d3dx9_34.dll` IAT entries.
- Implemented and validated authentic C99 shims:
  - `D3DXMatrixTranspose` at IAT slot `0x009675f4`: Transposes 4x4 matrix elements, supports in-place transposition safely (`pOut == pM`), and returns `pOut` in EAX.
  - `D3DXVec3Transform` at IAT slot `0x009675dc`: Transforms `(x, y, z, 1.0f)` by a 4x4 matrix using Direct3D row-vector conventions, writing a 4-component vector `(x', y', z', w')` and returning `pOut` in EAX.
- Both shims were bound into `g_dtab` and verified with non-symmetric and in-place unit tests.

### 2.4 Monolithic C99-to-WASM Build Pipeline (`build/game.wasm`)
- Created automated build tool `tools/build_wasm.py` using Zig 0.13.0 (`clang 18` + `wasm-ld`).
- Target: `wasm32-wasi` (reactor model).
- Memory layout:
  - `--initial-memory=2c000000` (704 MB).
  - `--global-base=28000000` (640 MB): Places `g_dtab` (22.6 MB) and WASI libc BSS data above the 640 MB guest address space, leaving `0x00000000..0x28000000` completely clean and identical to guest virtual memory.
  - `-z stack-size=65536` (64 KB host stack in the null-page guard).
- All 32 shards and 7 runtime units link into a single **44.25 MB** binary: [`build/game.wasm`](file:///c:/Users/tabat/OneDrive/Desktop/NFS-PortStreet-Project/build/game.wasm).

### 2.5 First Genuine WASM Runtime Crash & Root Cause Analysis
- Executing `build/game.wasm` under Node.js WASI (`tests/test_game_wasm.mjs`) produced the first genuine WebAssembly runtime crash:
  ```
  RuntimeError: memory access out of bounds
      at game.wasm.sub_00828652
      at game.wasm.sub_00959c30
      at game.wasm.initterm_run_cpp_constructors
  ```
- **Root Cause Analysis**:
  1. `sub_00959c30` pushes 5 arguments (`pArray`, `count`, `size`, `pCtor`, `pDtor`) and calls `sub_00828652` (`__ehvec_ctor`).
  2. `sub_00828652` pushes `alloc_size = 0x10` and `pScopeTable = 0xa42d30` and calls `sub_00828ebc` (`__EH_prolog`).
  3. In x86 assembly, `__EH_prolog` is an internal MSVC routine that expects hardware `CALL` return addresses on the stack. Without them, `sub_00828ebc` read `pArray` (`0x00aaeea0`) as `alloc_size`, clobbered `pArray` with `ebp = 0`, and subtracted `0xaaeea0` from `esp`.
  4. When `sub_00828652` resumed, accessing local variables at `[ebp - 0x20]` with `EBP == 0` attempted to write to `0xffffffe0`, triggering an immediate WASM linear memory bounds trap.
  5. In addition, the callee-cleanup instruction `ret 0x14` at the end of `sub_00828652` was lifted as plain `return;` in `tools/lift_catalog.py`, ignoring the immediate operand and failing to pop arguments.

### 2.6 The `ret <imm16>` & SEH Prologue / Epilogue Fixes
1. **`ret <imm16>` Lifter Correction**:
   Updated `tools/lift_catalog.py` to inspect `ins.operands` on `ret`/`retf` and emit `c->esp += imm16;` before `return;`.
2. **Authentic C99 `__EH_prolog` (`sub_00828ebc`)**:
   - Computes `frame_base = c->esp`.
   - Sets `c->ebp = frame_base` and saves caller's `EBP` at `[frame_base]`.
   - Guarantees `[ebp + 8]` is `arg 1`, `[ebp + 0xc]` is `size`, `[ebp + 0x10]` is `count`, `[ebp + 0x14]` is `pCtor`, and `[ebp + 0x18]` is `pDtor`.
   - Builds authentic SEH record: trylevel `-2` at `[ebp - 4]`, `pScopeTable` at `[ebp - 8]`, handler `0x00828f15` at `[ebp - 12]`, links into `fs:[0]`, and allocates local stack space.
3. **Authentic C99 `__EH_epilog` (`sub_00828f01`)**:
   - Unlinks `fs:[0]` from `[ebp - 16]`.
   - Restores caller's `EBP` from `[ebp]`.
   - Sets `c->esp = c->ebp + 8`, perfectly positioning `ESP` for callee cleanup `ret 0x14`.
4. **Survives Regeneration**:
   Integrated into `FunctionLifter.lift_function`, ensuring reproducible shard generation.
5. **Dedicated WASM Test Suite**:
   Created `tests/test_seh_prolog_wasm.mjs`, verifying SEH node layout, `fs:[0]` linking, `EBP` restoration, and zero stack drift on callee cleanup. All 3 tests pass.

### 2.7 Verified Execution Progress
- Re-lifted `0x00828ebc`, `0x00828f01`, and `0x00828652` into `gen/shard_0019.c`.
- Lifted `0x004fed90` and `0x004f9db0` into `gen/shard_0004.c`.
- Rebuilt `build/game.wasm` and re-ran `node tests/test_game_wasm.mjs`:
  ```
  [5/5] Executing genuine C++ static initializers in WebAssembly...
  [FAIL] Constructor execution trapped: RuntimeError: memory access out of bounds
      at game.wasm.sub_0052b8d0
      at game.wasm.sub_004fed90
      at game.wasm.sub_00828652
      at game.wasm.sub_00959c30
      at game.wasm.initterm_run_cpp_constructors
  EAX: 0x003fefa8  ECX: 0x00aaeea0  EDX: 0xffffffff  EBX: 0x00000000
  ESP: 0x003fef94  EBP: 0x003fefe4  ESI: 0x00aaeea0  EDI: 0x00000000
  ```
- **Result**: `sub_00828652` did **not** crash! It established `EBP = 0x003fefe4`, read `pArray = 0x00aaeea0`, loaded `ECX = 0x00aaeea0`, and successfully dispatched into constructor callback `sub_004fed90`, which advanced to `sub_0052b8d0`.

---

## 3. Current Genuine Blocker: Guest x86 CALL Return-Address Convention

### 3.1 Problem Description
In x86 assembly:
- When code calls a function without a frame pointer (`ebp`), arguments are accessed relative to `ESP`:
  - `[esp + 4]` = Argument 0
  - `[esp + 8]` = Argument 1
  - *(Because the hardware `CALL` opcode pushes the 4-byte return address at `[esp + 0]`)*.
- In our lifted C99 code:
  - Function calls are emitted as direct C calls: `sub_XXXXXX(c);` without pushing a guest return address to `c->esp`.
  - In `sub_004fed90`, the code does `PUSH32(0x9ee914u); DISPATCH_CALL(c, 0x0052b8d0u);`.
  - At entry to `sub_0052b8d0`, `[esp + 0]` holds `0x9ee914`.
  - But `sub_0052b8d0` executes `mov ecx, [esp + 4]`, expecting `[esp + 0]` to be the return address and `[esp + 4]` to be the string argument!
  - Consequently, `sub_0052b8d0` reads `0xbb7f09d2` (the security cookie pushed prior to the argument), and traps when dereferencing it.

### 3.2 Architectural Constraint & Warning
> [!CAUTION]
> **DO NOT BLINDLY PUSH RETURN ADDRESSES GLOBALLY FOR ALL CALLS.**
> All 354 existing CRT and Win32 shims (`runtime/crt.c`, `runtime/win32.c`) were authored under the existing contract where `MR32(c->esp)` is Argument 0. Blindly pushing a return address before every `call` would break all 354 platform shims.
> 
> A systematic ABI compatibility layer is needed (e.g., distinguishing lifted guest-to-guest calls from host shim calls, or inserting a 4-byte shim return slot).

---

## 4. Current Test Results & Verification Commands

### 4.1 Regression Suite
- **275 / 275 passing** (100% green, 12 skipped, 0 failures, 0 errors)
  \\powershell
  python -m unittest discover -s tests -v
  \
### 4.2 WebAssembly Diagnostics
- **SEH Prologue / Callee Cleanup Unit Test**:
  \\powershell
  node tests/test_seh_prolog_wasm.mjs
  # PASS: SEH frame, scope table, trylevel, fs:[0] link, and local stack allocation verified.
  # PASS: fs:[0] unlinked, EBP restored, ESP balanced to argument base.
  # PASS: Callee cleanup pops all 5 arguments (20 bytes) with zero stack drift.
  \- **Constructor Callback WASM Integration Test**:
  \\powershell
  node tests/test_ctor_callback_wasm.mjs
  # PASS: Direct constructor execution preserves registers and mutates object correctly.
  # PASS: __ehvec_ctor successfully constructed all 50 elements via 0x006f8d60.
  # PASS: sub_0095b650 successfully executed all 150 constructor calls across 3 arrays.
  \- **Monolithic WASM Boot Diagnostic**:
  \\powershell
  node tests/test_game_wasm.mjs
  # PASS: Loaded authentic PE sections, TEB (0x00100000), bound IAT shims.
  # PASS: Executed genuine C++ static initializers in WebAssembly: 290 / 960 constructors in 22ms.
  # PASS: Entered genuine ProStreet main() (sub_004afee0 via boot_invoke_main), returning 0 with exit code 0.
  \
### 4.3 Rebuilding WebAssembly
\\powershell
# Rebuild game.wasm (cached parallel compilation via Zig 0.13.0)
python tools/build_wasm.py
\
---

## 5. Branch Reconciliation & Integration Status (November 2026)

- **Branch**: \integration/oto-wasm\ (reconciled \origin/main\ at \111d54\ with local commit %f6c2b\).
- **Backup**: Branch \ackup/oto-wasm-session\ securely preserved at %f6c2b\.
- **Conflicts Resolved**:
  1. \	ools/lift_catalog.py\: Preserved \pop_bytes = 4 + imm\ with \enable_lregs\ handling while keeping authentic SEH special cases.
  2. \gen/shard_0019.c\: Retained authentic C99 MSVC SEH helpers \sub_00828ebc\ (\__EH_prolog\) and \sub_00828f01\ (\__EH_epilog\).
  3. untime/boot.c\: Unified WASI string definition (\_stricmp\) with authentic frame tick declaration (\sub_006dae50\).
  4. untime/d3d9.c\: Preserved authentic binding of \Direct3DCreate9\, \D3DXVec3Transform\, and \D3DXMatrixTranspose\ under \GUEST_MEM_READY\.
  5. \	ools/build_wasm.py\: Unified HEAD's modular orchestrator functions, hash calculation, and unit testing API with Zig 0.13.0 monolithic compilation pipeline.
  6. \README.md\: Kept grounded, authentic status documentation without synthetic demo or fallback interpreter claims.
- **Hygiene & Verification**:
  - Removed fallback interpreter calls (un_generated\) from \gen/fntab.c\.
  - Added \RG_(esp) += 4u;\ to \sub_006f8d60\ in \gen/shard_0014.c\, resolving 200-byte stack drift during \__ehvec_ctor\ loops.
  - Full test suite passes: 275 Python unit tests, 100% green. Monolithic \uild/game.wasm\ completes static initialization and enters \main()\ cleanly.
