# PortSpeed Project Status Report

> **Current State, Static Recompilation Progress, Blockers, and Next Steps**  
> *Last Updated: October 31, 2026*

---

## 1. Executive Summary

PortSpeed is an experimental project investigating static binary recompilation of the original 2007 PC game **Need for Speed: ProStreet v1.1** to native WebAssembly and modern browser technologies (TypeScript, WebGL2).

Development is currently suspended. This document records the exact working state, completed experiments, verified facts, current blockers, and the recommended plan for resumption.

---

## 2. Completed Milestones & Accomplishments

### Phase 1: Read-Only Reconnaissance
- Verified inventory scanner across **3,362 original files** (`5,638,443,663` bytes) without modifying timestamps or original bytes.
- PE analysis of three executable binaries in the installation:
  - `Need For Spped - Pro Street/nfs.exe` (`28,739,656` B, SHA-256 `ee8a71c7c1...`): Primary unpacked target (`RawOffset == RVA` throughout all 10 sections) built with Visual Studio 2005 SP1 (MSVC 8.0, build `50727`).
  - `Need For Spped - Pro Street/nfs.exe.org` (`13,120,776` B, SHA-256 `8f515be62a...`): SecuROM v7.35 encrypted binary (`EuropeRelease`).
  - `Need For Spped - Pro Street/Crack.1.1-ViTALiTY/nfs.exe` (`3,765,248` B, SHA-256 `2983cd2821...`): UPX-compressed distribution.

### Phase 2: Native Texture Pipeline & WebGL2 Viewer
- Authored WebAssembly DXT1/DXT3/DXT5 decoders in AssemblyScript (`web/assembly/bc3.ts` -> `bc3.wasm`).
- Parsed standalone Version 8 TPK (`0xB3300000`) containers.
- Cross-validated **34 original game textures** (`22` original `DXT5` + `1` `DXT3` in `GLOBAL/` containers + `11` compressed textures in `CARS/240SX/TEXTURES.BIN`) with **100% pixel-exact parity (`max_diff == 0`)** against Pillow 13.0.0 DDS decoding and WebGL2 `readPixels`.

### Phase 3A: Static Recompilation of Asset Decompression Pipeline
- Reverse-engineered and disassembled the original game's decompression routines in `nfs.exe` `.text`:
  - `sub_006cd550`: `LZDecompress_JDLZ` (`0x5a4c444a` LZ77 decompressor).
  - `sub_006cd6a0` / `sub_006cfc10`: `LZDecompress_HUFF` (`0x46465548` RefPack Huffman + RLE + Delta).
  - `sub_006d3cd0`: `LZDecompress_Dispatch` (single-block magic dispatcher).
  - `sub_006d3e20`: `CIP_DecompressStream` (`0x55441122` multi-block stream dispatcher).
- Built static x86 lifter (`experiments/recomp/lift_x86.py`, `experiments/recomp/x86_cpu.h`) lifting **11 functions (`4,407` bytes `.text`, `1,518` instructions)** to C99 and WebAssembly (`prostreet_lifted.wasm`, `42,522` bytes).
- Reverse-engineered `CARS/240SX/GEOMETRY.BIN` (`0x80134000`, `1,141` `eSolid` parts) and built an isolated WebGL2 3D mesh viewer with orbit camera rendering the stock 240SX vehicle-space body (`14,612` triangles).

### Phase 3B: Guest Memory Loader & Static C++ Initializer Proof of Concept
- Implemented checked PE section memory loader (`experiments/recomp/guest_memory.py`) loading `.rdata` and `.data` into WebAssembly linear memory at authentic guest virtual addresses.
- Implemented indirect guest call dispatcher `callGuestFunction(funcVa: u32)`.
- Lifted and executed genuine static C++ initializer **`sub_00959ca0` (`_initterm` slot 45)** in WebAssembly:
  - Verified return value in `EAX == 0x00000000`.
  - Verified caller stack balance (`ESP == stackPtr`).
  - Verified callee-saved registers (`EBX`, `ESI`, `EDI`, `EBP`) preserved.
  - Verified observable guest memory mutation: registered node descriptor `0x00a4af2c` into `.data` linked list head `[0x00ab08c8]`.

---

## 3. Comparison with Existing Prior Art

| Architecture Feature | `th0mk/nfsu2-web` (NFS Underground 2) | `veritr1x/recomp-kit` (NFS Most Wanted) | PortSpeed (NFS ProStreet) |
|---|---|---|---|
| **Disassembly Pipeline** | Standalone Python + Capstone on PE sections | Ghidra headless `ExportProgram.java` | Direct Python + Capstone on `nfs.exe` PE sections |
| **Guest Memory Model** | 1:1 guest VA mapping into WASM linear memory (`IMAGE_BASE=0`) | Relative pointer `g_mem_base + addr` with macro accessors | **1:1 guest VA mapping into WASM linear memory** (`0x00400000..0x02000000`) |
| **Code Sharding** | Sharded into 32 translation units (`gen_00.c` .. `gen_31.c`) | Per-function files compiled to static lib | Monolithic test module; sharder designed for Phase 4 |
| **CRT & Imports** | Static CRT overrides by VA | SDL3 + native D3D9/D3DX9 layer | Intact `OriginalFirstThunk` IAT reconstruction at `RVA 0x00647a7c` |

---

## 4. Current Blockers & Challenges

1. **SecuROM Virtualized Prologues (`2,153` Trampolines)**:
   - `nfs.exe` contains 2,153 indirect jumps (`ff 25`) into `.securom` stubs.
   - For startup, the entry trampoline at `main` (`VA 0x004afee0`) must be resolved to its native MSVC stack frame prologue (`push ebp; mov ebp, esp; and esp, 0xfffffff8; sub esp, 0x74; jmp 0x004afef2`).
   - The 221 countdown check stubs (`dec dword ptr [0x01a6xxxx]; je ...`) must be statically nopped.
2. **`_initterm` C++ Static Initializer Dependencies**:
   - Out of the 960 initializers, 269 are leaf functions that can execute now.
   - Approximately 450 initializers call `sub_0082851b` (`__onexit` / `atexit` registration helper) and push destructor function pointers in `.text`. An `atexit` list dispatcher is required before running the full batch.
   - Floating-point initializers (such as Slot 5 `sub_009597d0`) require x87 FPU stack emulation (`fld`, `fstp`, `fdivrp`).
3. **Full ISA Instruction Coverage**:
   - `nfs.exe` contains `101,566` x87 FPU instructions and `31,878` SSE/SSE2 instructions. A complete lift of `.text` requires porting `nfsu2-web`'s x87 stack and SIMD128 helper implementations.

---

## 5. Recommended Next Milestone for Resuming Development

### Milestone: Full Leaf Initializers & `atexit` Dispatcher
1. **Extend `lift_x86.py`** to lift the 269 leaf initializers from the `_initterm` constructor table.
2. **Implement `__onexit` / `atexit` shim**: Hook `sub_0082851b` in guest memory to capture registered destructor function pointers in a WebAssembly table.
3. **Batch-execute initializers**: Execute all non-floating-point initializers in sequence and verify global engine subsystem registration in `.data`.

---

## 6. Verification Summary (Preserved Baseline)

- **Python Tests**: `37/37 passed` in `0.021s` (`tests/test_guest_memory.py`, `test_lifter.py`, `test_geometry.py`, `test_archives.py`, `test_recon.py`, `test_tpk.py`).
- **Static Initializer Test**: `node experiments/recomp/test_initializer.mjs` passed (`sub_00959ca0` mutation verified).
- **Static Recompilation Full Asset Test**: `node experiments/recomp/verify_recomp.mjs` passed (33 textures + 12 geometry streams verified in WebAssembly).
- **Web Unit Tests & Production Build**: `8/8 passed`, Vite build cleanly generated.
- **Playwright Browser Test**: Headless Chrome WebGL2 verified 33 textures + 240SX 3D mesh rendering.
- **Executable Protection**: Original game executables verified byte-identical (`tools/identify_executables.ps1`).
