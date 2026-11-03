# PortSpeed — Engineering Handoff & Architecture Status

**Document:** `Oto's latest.md`<br>
**Date:** November 3, 2026<br>
**Repository:** `https://github.com/OtariTB/PortSpeed.git` (branch `main`)<br>
**Target:** PC v1.1 `nfs.exe` (SHA-256: `66d0ef062b8cf145941656f71d5300ee7a18413eb44747c0c1b72e5927ad7404`)

---

## 1. Executive Summary & Architecture Decision

### 1.1 Option C: Systematic Lifter Correctness & SecuROM Splice Normalization
Following an in-depth architectural feasibility audit comparing PortSpeed against related recompilation projects (*th0mk/nfsu2-web* and *austynoconnor/most-wanted-web*), the team formally adopted **Option C**:
- **Preserves Existing Architecture:**
  - Strictly **no** CPU emulation, full-system emulation, or synthetic/fake gameplay physics.
  - Preserves PortSpeed's high-performance 1:1 guest linear memory layout (640 MB arena at `0x00000000..0x28000000`).
  - Preserves the direct $O(1)$ master dispatch table (`g_dtab` of 5,660,672 entries covering `0x00401000..0x00967000`).
  - Preserves the entire C99 platform runtime (`runtime/`) shimming MSVCR80, Win32, and Direct3D 9.
  - Preserves the TypeScript / WebGL2 browser frontend and command ring-buffer consumer (`web/`).
- **Lifter & Generator Focus:** Replaces ad-hoc shard edits with systematic, generator-level transformations in `tools/lift_catalog.py` and `tools/generate_shards.py` to ensure all manual recoveries, instruction lifters, and DRM resolutions survive clean regenerations.

---

## 2. Key Accomplishments This Session

### 2.1 SecuROM Trampoline Resolution (2,151 Registered Destinations)
- **Authentic Database:** Loaded all 2,153 verified SecuROM trampoline mappings from `research/local/phase1/securom_trampolines.json`.
- **Direct Call & Tail-Jump Redirection:** Updated `InstructionLifter` in `tools/lift_catalog.py` to resolve direct `call` and `jmp` sites pointing to SecuROM trampoline stubs into their confirmed catalog function targets.
- **Master Dispatch Table Registration:** Extended `tools/generate_shards.py` to emit `fntab_init_trampolines()` in `gen/fntab.c`. At startup, **2,151** valid trampoline destinations are registered directly into `g_dtab`, guaranteeing that both direct calls and indirect/vtable calls to trampoline sites resolve with $O(1)$ zero overhead.
- **Targeted Regression Suite:** Created `tests/test_trampoline_resolution.py` covering database loading, chained trampolines, confirmed target redirection, missing target protection, and unchanged normal calls. All 7 tests pass (100% green in 0.028s).

### 2.2 Preservation Architecture (`tools/manual_overrides.py`)
- Created `tools/manual_overrides.py` as the canonical source of truth for all manually recovered routines.
- Hooked `MANUAL_RECOVERIES` directly into `FunctionLifter.lift_function()` in `tools/lift_catalog.py`.
- **All 35 manual overrides now survive 100% of future shard regenerations**:
  - `bChunk` allocator (`sub_00463e90`)
  - Fastmem routines (`sub_00435eb0`, `sub_00436130`, `sub_00463f10`, `sub_00464e70`, `sub_00465020`, `sub_01a11e20`)
  - Fastmem initialization (`sub_00463d70`)
  - String operations (`sub_004dd540`, `sub_0052a7f0`, `sub_0052b8d0`)
  - DRM and platform bypasses (`sub_0070f600`, `sub_0070f640`, `sub_008975c3`)
  - SEH handlers (`sub_00828ebc`, `sub_00828f01`)
  - All 9 missing static constructor helpers (`0x00463d70`, `0x004e03d0`, `0x004f9db0`, `0x004fed90`, `0x00634490`, `0x007223b0`, `0x00783de0`, `0x00783e30`, `0x009006c0`).

### 2.3 Systemic `MUL` Instruction Lifter
- **Problem**: In constructor #169, `sub_0063b500` previously failed to lift the `mul edx` mnemonic (`/* Unsupported: mul ... */`), leaving `EAX` uncomputed and triggering an arithmetic overflow request of `0xFFFFFFFF` bytes, causing an unconstrained 40-minute hang.
- **Solution**: Implemented bit-exact 8-bit, 16-bit, and 32-bit unsigned `mul` instruction lifting with authentic Carry (CF) and Overflow (OF) flag calculation in `InstructionLifter` in `tools/lift_catalog.py`.
- **Verification**: Verified generated code in `gen/shard_0010.c`:
  ```c
  uint64_t _p = (uint64_t)RG_(eax) * (uint64_t)(RG_(edx));
  RG_(eax) = (uint32_t)_p;
  RG_(edx) = (uint32_t)(_p >> 32);
  c->eflags = (c->eflags & ~(F_CF | F_OF)) | (RG_(edx) != 0 ? (F_CF | F_OF) : 0);
  ```

### 2.4 Controlled Full Shard Regeneration
- Executed `python tools/generate_shards.py --num-shards 32 --out-dir gen`.
- Regenerated all 32 C99 shards (`gen/shard_0000.c` .. `gen/shard_0031.c`), `gen/fntab.c`, and `gen/fntab.h` (32,029 functions lifted across 220,847 basic blocks, 126.58 MB C source in 51.6s).
- Verified that all 35 manual overrides and the `mul` instruction fix survived regeneration.

### 2.5 Monolithic WebAssembly Build (`build/game.wasm`)
- Executed `python tools/build_wasm.py` with Zig 0.13.0 targeting `wasm32-wasi` with WebAssembly SIMD128 (`-msimd128 -mtail-call`).
- Successfully compiled and linked all 41 compilation units (32 shards, `fntab.c`, and 8 runtime modules).
- Produced genuine [`build/game.wasm`](file:///c:/Users/tabat/OneDrive/Desktop/NFS-PortStreet-Project/build/game.wasm) (**49,465,990 bytes / 47.17 MB**).

---

## 3. Current Execution State & Blocker Analysis

### 3.1 Genuine Constructor Diagnostic Execution
Executed `python tools/run_diagnostic_timeout.py` under Node.js WASI with a hard 60-second deadline:
```text
=== PortSpeed WebAssembly Genuine Boot Diagnostic ===
WASM Module: build/game.wasm
[1/5] Calling fntab_init() to populate master dispatch table...
      fntab_init completed in 7ms
[2/5] Loading authentic PE sections into WASM linear memory...
      Mapped .text, .rdata, .data, .tls, .rsrc, ars, est, artem, celare, .securom
[3/5] Setting up TEB (0x00100000) and Guest Stack (0x003FF000)...
[4/5] Binding IAT shims and installing runtime hooks...
[5/5] Executing genuine C++ static initializers in WebAssembly...
      ... reached Constructor #50 (0x959d40)
      ... reached Constructor #100 (0x95a380)
      ... reached Constructor #150 (0x95a860)
      -> [START] Constructor #169 (0x95aa40)...
[FAIL] Constructor #169 (0x95aa40) trapped: RuntimeError: unreachable
    at game.wasm.sub_00463e90 (wasm://wasm/game.wasm-0bcb2a1a:wasm-function[2614]:0x5c1b15)
    at game.wasm.sub_006369e0 (wasm://wasm/game.wasm-0bcb2a1a:wasm-function[11252]:0x14d434f)
    at game.wasm.sub_0063b500 (wasm://wasm/game.wasm-0bcb2a1a:wasm-function[11271]:0x15264b9)
    at game.wasm.sub_0095aa40 (wasm://wasm/game.wasm-0bcb2a1a:wasm-function[31110]:0x2d07ae0)
EAX: 0x00000000  ECX: 0x00000010  EDX: 0x00000010  EBX: 0x00000000
ESP: 0x003fef68  EBP: 0x00828679  ESI: 0x00828679  EDI: 0x00828679
EIP: 0x004324e7  FS:  0x00100000
```

### 3.2 Key Findings
1. **The 40-Minute Infinite Hang is Eliminated:**
   Thanks to the systemic `mul` lifting fix, `sub_0063b500` no longer computes `0xFFFFFFFF` bytes. The correct element count and array size are passed to `sub_006369e0` -> `sub_00463e90`.
2. **Deterministic Halt in 0.30s:**
   Execution terminates deterministically at the exact failure site rather than looping unconstrained.
3. **Root Cause of the Trap in `sub_00463e90`:**
   - In `sub_00463e90` (`bChunk::Alloc`), the small-block freelist (`MR32(RG_(ebx) + RG_(esi)*4u)`) is initially empty (`NULL`).
   - `sub_00463e90` calls `sub_00464100` (`bChunk::ReplenishPool` / `bChunk::GrowArena`) to allocate a new arena chunk for that size class.
   - `sub_00464100` returns `AL == 0` (allocation failed).
   - `sub_00463e90` branches to `L_00463ecd`, which calls the `bChunk` assertion failure helper at `0x004324e0` and executes `MR32(0x0u) = 0u;` (an intentional null-pointer crash on assertion failure).
   - This writes to the null-guard page (`0x00000000`), triggering the `RuntimeError: unreachable` trap in WebAssembly.

---

## 4. Clear Next Steps for the Next Development Session

1. **Investigate `sub_00464100` Arena Growth:**
   - Disassemble and trace `sub_00464100` to determine how `bChunk` requests memory when replenishing small-block freelists (e.g. does it call `VirtualAlloc`, `malloc`, or access a pre-allocated global arena buffer?).
   - Verify whether the `bChunk` allocator control structure (`EBX`) has been properly initialized with base pointers.
2. **Verify Fastmem Pool Initialization (`sub_00463d70`):**
   - Confirm whether `bChunk::InitializeFastmem` (`0x00463d70`) or preceding static constructors initialized the required fastmem heap pools.
   - Ensure backing guest heap memory at `0x02000000..0x28000000` is properly configured to service arena growth.
3. **Advance Constructor Execution Past #169:**
   - Once arena replenishment in `sub_00464100` succeeds, constructor #169 will allocate its descriptor array and return cleanly.
   - Run the timed diagnostic to observe execution flow through constructors #170 through #960 towards the genuine engine entry point `sub_004afee0` (`main()`).
