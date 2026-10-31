# Static Recompilation Feasibility, Executable Analysis, and Phase D Proof of Concept

## 1. Current Project State Report (Phase A)

### 1.1 Existing Validated Capabilities
- **Read-Only Reconnaissance (`tools/recon.py`, `tools/identify_executables.ps1`)**:
  - Surveys `3,362` files (`5,638,443,663` bytes) in the protected user-supplied installation directory without modifying files or timestamps.
  - Parses PE32/PE32+ headers, sections, and static DLL import descriptors with synthetic unit tests covering malformed/truncated inputs and output path protection.
- **Asset & Container Parsers (`tools/tpk.py`, `tools/archives.py`, `tools/validate_assets.py`)**:
  - Validates standalone Version 8 TPK (`0xB3300000`) containers (`GLOBAL/LOADINGTEXTURES.BUN`, `GLOBAL/UniqueBootTextures.bin`, `GLOBAL/NISOverlayTextures.bin`) and decodes BC3/DXT5 base mip levels with **22/22 pixel-exact RGBA SHA-256 matches** against Pillow 13.0.0 DDS decoding (`ICON_STAR` RGBA SHA-256: `54b4be9413298327555a3b1005defa66cb11672e5fb9a0d373c8547fd0e1f5e7`).
  - Parses `BIG4` header/entry tables and `JDLZ` 16-byte headers (`0x5A4C444A`, version `0x02`).
- **Browser Texture Viewer & WebAssembly Decoder (`web/`)**:
  - TypeScript + Vite + WebGL2 viewer (`web/src/main.ts`, `web/src/tpk.ts`, `web/src/bc3.ts`, `web/src/webgl.ts`) paired with an AssemblyScript `0.28.20` BC3/DXT5 decoder (`web/assembly/bc3.ts` -> `web/public/bc3.wasm`).
  - User-selected `.bun`/`.bin` files are parsed locally in the browser, decoded in WebAssembly, and rendered via WebGL2 with `readPixels` verification.
- **Test & Build Status (Verified in Phase A)**:
  - `python -m unittest discover -s tests -v`: **23/23 existing tests passed** (`28/28` including Phase D synthetic lifter tests).
  - `npm --prefix web test`: **5/5 passed** (`asc` build + `tsx --test tests/core.test.ts`).
  - `npm --prefix web run build`: **Passed** (`asc` + `tsc --noEmit` + `vite build`).
  - `scratch/validation-env/Scripts/python.exe tools/validate_assets.py`: **Passed** (22/22 textures verified against Pillow 13.0.0).
  - `powershell -NoProfile -File tools/identify_executables.ps1`: **Passed** (all 3 executable SHA-256 hashes unchanged).

---

## 2. Technical Comparison of Existing Static Recompilation Frameworks (Phase B)

Shallow reference checkouts were inspected in gitignored `scratch/recomp-refs/`:
- `th0mk/nfsu2-web` at commit `a5545b759c4c06cad1a029c98e91cca92a396f6f` (`2026-10-30`, MIT License).
- `veritr1x/nfsmw-recomp` at commit `bb95925d5b58656b8b23e9df6eb0c9647be1bece` (`2026-09-21`, MIT License).
- `veritr1x/recomp-kit` at commit `487b94ac17bc10c4796dc4bce8d16ddbdeb7ec1d` (`2026-10-25`, MIT License).

| Dimension | `th0mk/nfsu2-web` (NFS Underground 2, 2004) | `veritr1x/nfsmw-recomp` + `recomp-kit` (NFS Most Wanted, 2005) | Suitability for PortSpeed (`nfs.exe`, 2007) |
|---|---|---|---|
| **Disassembly & Function Discovery** | Standalone Python + Capstone (`tools/lift.py`, `tools/genall.py`); discovers call targets directly from the PE image + dynamic trace seeds. | Requires Ghidra headless/GUI `ExportProgram.java` (`functions.tsv` + `functions/*.asm`) driven by `game.toml`. | **`nfsu2-web` approach preferred** as primary pipeline (direct Python + Capstone on PE sections without mandatory Ghidra export round-trips), supplemented by `recomp-kit` `analyze.py` ideas. |
| **Translation Model & Optimization** | Emits `void sub_XXXXXXXX(CPU *c)` into sharded `gen_00.c..gen_31.c`. Implements `LREGS` (local register promotion), `FLAGABI` (interprocedural dead-flag elimination), `JTSWITCH` (jump tables -> C `switch`), and `MERGECFG`. | Emits `void sub_XXXXXXXX(CpuState *cpu)` with `REG_EAX` macros and `goto loc_XXXXXXXX`. Includes a fallback runtime x86 interpreter (`runtime/interp.cpp`) for unlifted addresses. | **Hybrid**: `nfsu2-web`'s sharded C generation + flag dead-code elimination (`FLAGABI`) for performance, plus `recomp-kit`'s fallback interpreter concept for SecuROM VM stubs. |
| **Target Toolchain & Memory Model** | `wasi-sdk` (`clang --target=wasm32-wasip1-threads -O2`) directly to `.wasm`. Maps guest VAs (`0x00400000..`) 1:1 to WebAssembly linear memory offsets (`MEM8`/`MEM32` become single WASM load/store ops with `IMAGE_BASE=0`). | CMake + native Clang/MSVC or Emscripten (`SDL3` + WebGPU/Vulkan/Metal). Uses `MEM32(addr)` relative to `g_mem_base`. | **`nfsu2-web`'s 1:1 WASM linear memory model** (`wasm32`, guest VA == WASM address) eliminates base-pointer addition on every memory access in the browser. |
| **ISA Coverage (x87 / MMX / SSE)** | Full x86 integer, 8-deep x87 FPU stack (`double st[8]`), MMX, and scalar/packed SSE (`XMMReg xmm[8]`). | x86 integer, x87 FPU stack, basic MMX/SSE (`XmmReg xmm[8]`). | **Critical for ProStreet**: ProStreet uses **31,878 SSE/SSE2 instructions** alongside **101,566 x87 instructions**; `nfsu2-web`'s SSE lifter must be extended to full SSE2 integer/double precision. |
| **CRT & Win32 / DirectX Shims** | Hooks statically linked MSVC 7.1 CRT functions (`_malloc`, `_fopen`, `__ftol2`) by VA; serializes D3D9 draw calls + FVF vertices into a shared-memory command buffer consumed by TypeScript WebGPU; `AudioWorklet` for DSound. | Hooks statically linked CRT by VA; implements COM vtables in `dx/d3d9.cpp` and `dx/d3dx9.cpp` (`ID3DXEffect` vtable + `.fx` resource extraction for 31 embedded effects). | **Easier CRT in ProStreet, D3DX9 Effect overlap with `nfsmw-recomp`**: ProStreet imports `MSVCR80.dll` (156) and `MSVCP80.dll` (3) via IAT rather than static CRT linking, and embeds **34 `.fx` resources** loaded via `D3DXCreateEffectFromResourceA` just like Most Wanted. |

---

## 3. ProStreet Executable Analysis (Phase C)

### 3.1 Verified Facts: Executable Comparison & Identity
Three PE32 (`Machine = 0x014c` Intel 386, `ImageBase = 0x00400000`, `Subsystem = 3` Windows CUI) binaries exist in the protected installation directory:

| File (Relative to Game Root) | Size (Bytes) | SHA-256 | COFF Timestamp (UTC) | Export Module Name | Entry Point RVA / VA | Status |
|---|---:|---|---|---|---|---|
| `Need For Spped - Pro Street/nfs.exe` | `28,739,656` | `ee8a71c7c1e42923deb728e39a89317645cbcf26fc87cc48d3e07ade4dce2f72` | `1197239854` (`2007-12-09 22:37:34`) | `ProStreet08Release.exe` | `0x00428c25` (`VA 0x00828c25` in `.text`) | **Primary target**: unpacked memory-aligned dump (`RawOffset == RVA`) with decrypted `.text` and ViTALiTY SecuROM bridge at `VA 0x01ba1000`. |
| `Need For Spped - Pro Street/nfs.exe.org` | `13,120,776` | `8f515be62a479a4ccc5f0d6b0270be793c5fdeb7f5172d0b77ce182f24afc529` | `1200350722` (`2008-01-14 22:45:22`) | `ProStreet08EuropeRelease.exe` | `0x012bda10` (`VA 0x016bda10` in `est`) | Encrypted SecuROM v7.35 wrapper (`entropy = 7.637` in `.text`, `8.000` in `ars`); different regional build (`EuropeRelease`). |
| `Need For Spped - Pro Street/Crack.1.1-ViTALiTY/nfs.exe` | `3,765,248` | `2983cd2821d5da3565757ad829292e29dc51fbcadf1c1d1c46c06d4439522af5` | `1197239854` (`2007-12-09 22:37:34`) | *(compressed)* | `0x01aaa080` (`VA 0x01eaa080` in `.IN`) | UPX-compressed distribution of `nfs.exe` (`.ROT`, `.IN`, `.HEAVEN` sections; identical Rich header key `0x05d0e0b5`). |

### 3.2 Verified Facts: Compiler, Sections, and Startup Chain in `nfs.exe`
1. **Compiler & Linker Provenance**:
   - Intact Microsoft Rich Header at file offset `0x80..0x110` (`XOR key = 0x05d0e0b5`) identifies **Visual Studio 2005 SP1 (MSVC 8.0, build `50727`, Linker `8.0`)** with `@comp.id` entries for `Utc1400_CPP` (`prodid=110`, 929 C++ translation units), `Utc1400_C` (`prodid=109`, 359 C units), `Masm800` (`prodid=116`, 27 asm objects), and `Linker800` (`prodid=100`, build `50727`).
   - Embedded `RT_MANIFEST` (`RVA 0x00ce9560`, 338 bytes) requests side-by-side assembly `Microsoft.VC80.CRT` version `8.0.50608.0`.
2. **Section Layout (`RawOffset == RVA` and `RawSize == VirtualSize` across all 10 sections)**:
   - `.text`: `VA 0x00401000..0x00967000` (`5,660,672` B, entropy `6.648`, `0x60000020` RX) — decrypted x86 code.
   - `.rdata`: `VA 0x00967000..0x00a4a000` (`929,792` B, entropy `5.561`, `0x40000040` R) — IAT (`0x00967000..0x00967608`), C++ initializer tables (`__xc_a` at `0x00967608..0x0096a1f4`), RTTI, vtables, and string constants.
   - `.data`: `VA 0x00a4a000..0x01010000` (`6,053,888` B, entropy `0.379`, `0xC0000040` RW) — global state and BSS.
   - `.tls`: `VA 0x01010000..0x01011000` (`4,096` B, entropy `0.000`, `0xC0000040` RW) — TLS template (`0x01010000..0x01010008`, 8 zero bytes), TLS index at `VA 0x0100e43c`, empty callback array at `VA 0x0096a20c`.
   - `.rsrc`: `VA 0x01011000..0x010ea000` (`888,832` B, entropy `3.739`, `0x40000040` R) — **34 compiled D3DX9 `.fx` shader binaries** (`RT_RCDATA`), icon, cursor, version info (`1.1.0.0`), and manifest.
   - Five SecuROM v7.35 sections (`E:\vfdev-SecuROM-DRM_7_35\SecuROM_DRM\Wrapper\wrapper.pdb` string at `VA 0x019a12d6`): `ars` (`VA 0x010ea000`, `6,094,848` B), `est` (`VA 0x016ba000`, `32,768` B), `artem` (`VA 0x016c2000`, `3,051,520` B), `celare` (`VA 0x019ab000`, `24,576` B), and `.securom` (`VA 0x019b1000`, `5,994,466` B).
3. **Entry Point & Initialization Chain**:
   - `VA 0x00828c25` (`mainCRTStartup`): calls `__security_init_cookie` (`VA 0x00829163`) and jumps to `__tmainCRTStartup` (`VA 0x008289cd`).
   - `__tmainCRTStartup`: initializes thread-local/CRT state, runs `_initterm_e(0x0096a1f8, 0x0096a204)` (2 C initializers: `0x00828f09`, `0x00828749`) and `_initterm(0x00967608, 0x0096a1f4)` (**2,811 table slots containing 960 non-null C++ static constructor pointers, all 960 residing inside `.text`**), and invokes ProStreet's `main(argc, argv, envp)` at **`VA 0x004afee0`**.

### 3.3 Verified Facts: SecuROM v7.35 Virtualized Prologues & ViTALiTY Bridge
Static disassembly of `.text` revealed a critical architectural fact that any static recompiler for `nfs.exe` must handle:
1. **Pure vs. Hooked `.text` Functions**:
   - Recursive control-flow + prologue analysis across `.text` discovered **23,594 functions** (`1,023,088` instructions, `3,288,838` bytes = `58.1%` of `.text`).
   - **22,284 functions (`94.4%`)** are pure MSVC 8.0 x86 functions that never reference SecuROM sections.
   - **1,310 reachable functions (`5.6%`, with `2,153` total `ff 25` jump sites across `.text`)** have had their entry prologues or basic blocks replaced with a 6-byte indirect jump `ff 25 <addr_in_.securom>` (`jmp dword ptr [0x019exxxx]`).
2. **How the 2,153 `.securom` Trampolines Work**:
   - Each pointer at `0x019exxxx` targets a per-site stub at `0x01a6xxxx` in `.securom` (for example, `main` at `VA 0x004afee0` jumps via `[0x019efb44]` to `0x01a666a9`).
   - The stub pushes a SecuROM VM bytecode pointer (`0x01a3xxxx`), a site ID, and the `.text` resume address (`0x004afef2` for `main`), then jumps via `0x0116668b` (`ars`) -> `[0x017c21f4]` (`artem`) to **`VA 0x01ba1000` (`.securom`)**.
   - `VA 0x01ba1000` is the **ViTALiTY loader/VM bridge** (identifiable by ASCII strings `< space for rent >` at `0x01ba1003` and `-[ Masses Against the Classes <.>>< ]-` at `0x01ba1063`). It acquires a self-modifying spinlock byte at `0x01ba1020`, initializes a VM context structure at `0x01ba4800`, invokes the SecuROM VM interpreter in `ars` (`VA 0x011b75e0`) to execute the obfuscated instructions (for `main`, setting up the stack frame `push ebp; mov ebp, esp; and esp, 0xfffffff8; sub esp, 0x74`), and returns to `0x004afef2` in `.text`.
3. **221 SecuROM Countdown Triggers**:
   - `.text` also contains `221` sites of the form `dec dword ptr [0x01a6xxxx]; je 0x01a6bcxx`. ViTALiTY patched the target stubs at `0x01a6bcxx` to simply reset the counter (`mov dword ptr [0x01a6xxxx], imm32`) and jump straight back to the next `.text` instruction. In a static recompiler, all 221 sites can be nopped (`nop`) statically.
4. **Dumped IAT vs. Reconstructed ILT (`OriginalFirstThunk`)**:
   - Because `nfs.exe` was dumped from a Windows XP SP2 process, the raw file bytes in the IAT (`FirstThunk` at `VA 0x00967000..0x00967608`) still hold live XP addresses (`0x7c80xxxx`) plus **3 SecuROM IAT hooks** (`KERNEL32.dll!TerminateProcess` -> `0x010ea664`, `LoadLibraryA` -> `0x010ea3c5`, `GetProcAddress` -> `0x010ea33b`).
   - However, the Import Lookup Table (`OriginalFirstThunk` at `RVA 0x00647a7c`) is **100% intact for all 371 imports**. Binding IAT slots from `OriginalFirstThunk` at load time automatically bypasses all 3 SecuROM IAT hooks.

### 3.4 Verified Facts: Calling Conventions, Instruction Profile, and Platform Dependencies
- **Calling Conventions & SIMD**:
  - `14,116` `ret` (`__cdecl` / leaf) and `12,400` `ret imm16` (`__stdcall` / `__thiscall` / `__fastcall`) instructions; `29,482` indirect calls/jumps (`call/jmp reg` or `call/jmp [mem]` for C++ vtables, IAT calls, and switch tables).
  - Heavy floating-point and SIMD utilization: **`101,566` x87 FPU instructions**, **`31,878` SSE/SSE2 (`xmm`) instructions**, and **`2,240` MMX instructions**.
- **371 Imported Functions Across 15 DLLs**:
  1. **`MSVCR80.dll` (156) & `MSVCP80.dll` (3)**: Standard C/C++ runtime (`malloc`, `free`, `memcpy`, `memmove`, `fopen`, `fread`, `fseek`, `vsprintf`, `sscanf`, `_beginthread`, `_beginthreadex`, `_initterm`, `__CxxFrameHandler3`, `_CxxThrowException`, `std::basic_string` helpers). Because these are dynamically imported via the IAT, we do not need to hunt for inlined CRT signatures in `.text`.
  2. **`d3d9.dll` (1) & `d3dx9_34.dll` (14)**: `Direct3DCreate9`, `D3DXCreateEffectFromResourceA`, `D3DXCreateEffectPool`, `D3DXCreateCubeTextureFromFileInMemory`, `D3DXCreateVolumeTextureFromFileInMemory`, `D3DXSaveSurfaceToFileA`, `D3DXSaveSurfaceToFileInMemory`, `D3DXGetVertexShaderProfile`, `D3DXGetPixelShaderProfile`, `D3DXMatrixMultiply`, `D3DXMatrixMultiplyTranspose`, `D3DXMatrixTranspose`, `D3DXMatrixInverse`, `D3DXVec3Transform`, `D3DXVec4Transform`.
  3. **34 Embedded `.fx` Shaders in `.rsrc` (`RT_RCDATA`)**: Binary compiled D3DX9 effects (`01 09 ff fe` magic) including `IDI_CAR_FX`, `IDI_ROAD_FX`, `IDI_WORLD_FX`, `IDI_VISUALTREATMENT_FX`, `IDI_PARTICLES_FX`, `IDI_SKY_FX`, `IDI_FE_FX`, `IDI_SHADOWMAP_FX`, `IDI_SCREEN_EFX_FX`, etc., loaded at runtime via `D3DXCreateEffectFromResourceA`.
  4. **Input, Audio, Timing, Threading, Networking**:
     - `DINPUT8.dll`: `DirectInput8Create` (1).
     - `DSOUND.dll`: Ordinal 1 `DirectSoundCreate` (1).
     - `WINMM.dll`: `timeBeginPeriod`, `timeEndPeriod`, `timeGetTime` (3).
     - `KERNEL32.dll` (96): Win32 file I/O (`CreateFileA`, `ReadFile`, `SetFilePointer`, `FindFirstFileA`), synchronization (`CreateEventA`, `CreateMutexA`, `CreateSemaphoreA`, `WaitForSingleObject`, `EnterCriticalSection`, `InterlockedCompareExchange`), virtual memory (`VirtualAlloc`, `GlobalMemoryStatus`), threads (`CreateThread`, `SetThreadPriority`, `Sleep`).
     - `USER32.dll` (40): Window creation, message pump (`PeekMessageA`, `DispatchMessageA`), cursor/keyboard helpers.
     - `WS2_32.dll` (40), `NETAPI32.dll` (1), `ADVAPI32.dll` (11), `SHFOLDER.dll` (1), `RPCRT4.dll` (2), `ole32.dll` (1: `CoCreateInstance`).

### 3.5 Static Recompilation Feasibility Assessment (Deliverable 3)
- **Verified Verdict**: **Static recompilation of `nfs.exe` to C/WebAssembly is technically feasible**, provided the architecture explicitly addresses two ProStreet-specific requirements that did not exist in `nfsu2-web`:
  1. **SecuROM v7.35 Prologue Handling (`2,153` sites)**: While `94.4%` of reachable `.text` functions can be statically lifted directly to C/WASM today, the `2,153` `jmp dword ptr [0x019exxxx]` sites enter the SecuROM VM in `ars`/`.securom`. We have two viable paths (both avoiding x86 browser emulation of the game itself):
     - *Path 1 (Offline Symbolic/Unicorn Prologue Reconstruction — Recommended)*: Because each SecuROM VM stub executes only a short virtualized basic block (typically 3–10 stack-frame/register-setup instructions) before jumping back to a deterministic `.text` resume VA, an offline analyzer can run or symbolically trace each of the 2,153 stubs once against synthetic register states to synthesize equivalent native x86/C prologues.
     - *Path 2 (Hybrid Fallback Interpreter)*: Following `recomp-kit`'s `runtime/interp.cpp` pattern, execute the `94.4%` native `.text` code as ahead-of-time compiled WASM and invoke a bounded fallback interpreter only when control enters `0x010ea000..0x01f687c2` (`ars`/`.securom`) until it returns to `.text`.
  2. **Full SSE/SSE2 Instruction Lifting**: The lifter must support the `31,878` SSE/SSE2 instructions in `.text` (mapping 128-bit `XMM0..XMM7` operations to C/WASM `v128` SIMD128 or scalar helpers).
- **Hypotheses (Pending Verification)**:
  - *Hypothesis 1*: All 2,153 `.securom` VM prologues are pure register/stack-frame computations without external OS side effects. (Verified for `main` at `0x004afee0` -> `0x01a666a9`; remaining 2,152 stubs require automated batch classification.)
  - *Hypothesis 2*: `ole32.dll!CoCreateInstance` is used only for optional DirectShow/movie or network UPnP interfaces that can be stubbed during early engine bring-up.

---

## 4. Phase D Minimal Static Recompilation Experiment (Deliverable 4)

### 4.1 Experimental Pipeline (`experiments/recomp/`)
We built an isolated static recompilation pipeline (`experiments/recomp/lift_x86.py`, `experiments/recomp/x86_cpu.h`, `experiments/recomp/verify_recomp.mjs`, and `tests/test_lifter.py`) that:
1. Reads 4 genuine `.text` functions from `nfs.exe` read-only (verifying SHA-256 `ee8a71c7c1e42923deb728e39a89317645cbcf26fc87cc48d3e07ade4dce2f72`).
2. Recovers their basic-block control-flow graphs and translates every x86 instruction (`mov`, `movzx`, `movsx`, `lea`, `add`, `sub`, `or`, `and`, `xor`, `shl`, `shr`, `cmp`, `test`, `push`, `pop`, `jmp`, `je`, `jne`, `ja`, `jae`, `jb`, `nop`, `ret`) into:
   - **C99 (`prostreet_lifted.c`)** targeting `x86_cpu.h` (`X86Cpu *c`, `goto L_xxxxxxxx`), and
   - **AssemblyScript (`prostreet_lifted.ts`)** compiled via `web/node_modules/.bin/asc` to a standalone **WebAssembly module (`prostreet_lifted.wasm`, 5,380 bytes, SHA-256 `8bc826e7a2a845d3b6a4141c1840801c2e872148cf3ba97af98356e811430238`)** under `%LOCALAPPDATA%/NFSProStreetResearch/phase3/recomp`.

### 4.2 Lifted Functions & Verification Results (`node experiments/recomp/verify_recomp.mjs`)

| Function | VA Range in `nfs.exe` | Size | Basic Blocks / Insns | WebAssembly Verification Result |
|---|---|---:|---:|---|
| `sub_00436680` (`bStringHash`) | `0x00436680..0x004366a7` | 40 B | 5 BBs / 18 insns | **22/22 exact matches** against all 22 original ProStreet texture `name_hash` values in `research/local/phase2/assets.json` (`ICON_STAR` -> `0x86bd8901`, `FLIXFX_KING_SHOWDOWN` -> `0x05876490`, etc.), plus empty string (`0xffffffff`) and register/stack balance verification. |
| `sub_004366b0` (`bStringHashInit`) | `0x004366b0..0x004366d7` | 40 B | 5 BBs / 18 insns | **Verified**: `sub_004366b0("STAR", sub_00436680("ICON_")) == 0x86bd8901`. |
| `sub_004366e0` (`bStringHashUpper`) | `0x004366e0..0x00436713` | 52 B | 6 BBs / 23 insns | **22/22 exact matches** hashing lowercased texture names (`"icon_star"` -> `0x86bd8901`) to their uppercase TPK hash values. |
| `sub_006cd550` (`LZDecompress_JDLZ`) | `0x006cd550..0x006cd69c` | 333 B | 27 BBs / 114 insns | **100% byte-for-byte SHA-256 match**: rejects invalid magic/version (`returns 0`), decompresses synthetic JDLZ streams, and decompresses both 32 KiB original `JDLZ` blocks from `CARS/240SX/TEXTURES.BIN` (`@0x58180`, `18,045 -> 32,768` B and `16,882 -> 32,768` B) in WebAssembly with exact SHA-256 parity (`29ab7214...` and `0cb4d380...`). |

### 4.3 Bonus Format Discovery Enabled by Phase D (`CARS/240SX/TEXTURES.BIN` CIP Layout)
While validating the recompiled `sub_006cd550` (`LZDecompress_JDLZ`) on `CARS/240SX/TEXTURES.BIN` (`@0x58180`, compressed size `35,092`, advertised output `65,684`), we resolved the Phase 2 open question on `0x55441122` (`CIP`) multi-block streams:
- Each block inside a `CIP` stream begins with a 24-byte header `(u32 magic = 0x55441122, u32 uncompressed_size, u32 compressed_block_size, u32 uncompressed_target_offset, u32 compressed_stream_offset, u32 zero)`:
  1. **Block 0 (`+0`)**: `uncompressed_size = 32,768`, `compressed_block_size = 18,072`, `target_offset = 32,768` (`0x8000`), payload = `JDLZ` (`18,045` B).
  2. **Block 1 (`+18,072`)**: `uncompressed_size = 148`, `compressed_block_size = 112`, `target_offset = 65,536` (`0x10000`), payload = `HUFF` (`48 55 46 46`, EA Huffman-compressed 124-byte texture record + 24-byte format record trailer).
  3. **Block 2 (`+18,184`)**: `uncompressed_size = 32,768`, `compressed_block_size = 16,908`, `target_offset = 0` (`0x0000`), payload = `JDLZ` (`16,882` B).
- The three `compressed_block_size` values sum to `18,072 + 112 + 16,908 = 35,092` bytes, and the three `uncompressed_size` values sum to `32,768 + 148 + 32,768 = 65,684` bytes.

---

## 5. Concrete Next Development Milestone (Deliverable 5)

### Milestone: Phase 3A — Lift `HUFF` Decompressor + Multi-Block `CIP` Vehicle Texture & Geometry Pipeline
1. **Locate and statically lift ProStreet's `HUFF` (`0x46465548`) decompressor and `CIP` (`0x55441122`) block dispatcher from `nfs.exe` `.text`** into `experiments/recomp/lift_x86.py`, alongside `sub_006cd550` (`LZDecompress_JDLZ`).
2. **Validate full decompression of all 11 compressed vehicle textures in `CARS/240SX/TEXTURES.BIN`** (both the `JDLZ` pixel blocks and the 148-byte `HUFF` metadata trailers) and decode them in the browser texture viewer.
3. **Apply the validated `JDLZ`/`HUFF`/`CIP` decompressors to `CARS/240SX/GEOMETRY.BIN`** to inspect and document the uncompressed ProStreet vehicle mesh chunk hierarchy (`0x80134000`) for Phase 3 WebGL2 vehicle geometry viewing.
4. **Build a batch SecuROM trampoline classifier (`experiments/recomp/ inspect_securom_hooks.py`)** to catalog all `2,153` `jmp dword ptr [0x019exxxx]` sites in `nfs.exe` and verify automated prologue recovery starting with `main` (`VA 0x004afee0`).


---

## 6. Phase 3A Completed Milestone: Native `HUFF` + `CIP` Recompilation, Vehicle Textures, and 3D Geometry Decoding

### 6.1 Extended Static Lifter & Recompiled Decompression Pipeline (`experiments/recomp/`)
We extended `experiments/recomp/lift_x86.py` and `experiments/recomp/x86_cpu.h` to lift the complete compression call tree from `nfs.exe` `.text` (`11` functions, `4,407` bytes of `.text`, `306` basic blocks, `1,518` instructions) into C99 (`prostreet_lifted.c`, `86,294` B) and WebAssembly (`prostreet_lifted.wasm`, `42,072` B, SHA-256 `c23d4c0cfc1da3fd0c236e1528183595366330047127a898399dc431b9a36486`):
- Added instruction support for `call` (direct intra-module calls pushing the guest return VA onto the emulated stack), `sar`, `neg`, `inc`, `dec`, `imul` (1/2/3-operand forms), `adc`, `sbb`, `bswap`, `xchg`, `cdq`, `setcc` (`sete`, `setne`), signed conditional branches (`jl`, `jge`, `jle`, `jg`, `js`, `jns`), `rep stosd`, and `ret imm16`.
- Added stubbed guest hooks for two non-decompression side calls inside `sub_006d3cd0` and `sub_006d3e20`: `sub_006d1790` (byte-swap helper for big-endian `COMP` headers, unused on little-endian PC assets) and `sub_00436bf0` (engine memory pool free called only when `dst == NULL`).

| Symbol | VA Range in `nfs.exe` | Size | BBs / Insns | Verified Role & Calling Convention |
|---|---|---:|---:|---|
| `sub_006cd6a0` | `0x006cd6a0..0x006cd6f8` | 89 B | 6 / 30 | `uint32_t __cdecl LZDecompress_HUFF(const uint8_t *src, uint8_t *dst)` — checks `0x46465548` (`"HUFF"`) and `version == 1`, passes `src + 16`, `dst`, `comp_size`, `uncomp_size` to `sub_006cfc10`, and returns `uncomp_size` (`u32[2]`). |
| `sub_006cfc10` | `0x006cfc10..0x006d07b5` | 2,982 B | 190 / 1,037 | `int __cdecl HUFF_DecodeBody(const uint8_t *src, uint8_t *dst, int comp_size, int uncomp_size)` — decodes 16-bit big-endian option header (`0x30fb` raw, `0x32fb` 1st-order byte delta, `0x34fb` 2nd-order byte delta, `+0x8000` flag), 24-bit internal length, 8-bit RLE escape symbol, Exp-Golomb code-length counts, canonical Huffman symbol table, and bitstream symbols/RLE runs. |
| `sub_006cfbc0` | `0x006cfbc0..0x006cfc0c` | 77 B | 3 / 32 | `__fastcall` Exp-Golomb VLC reader (`ecx = bit_accum`, `edx = &bit_avail`). |
| `sub_006cfb40` | `0x006cfb40..0x006cfbb3` | 116 B | 3 / 47 | `__cdecl` bitstream refill helper. |
| `sub_006cfac0` | `0x006cfac0..0x006cfb36` | 119 B | 5 / 46 | `__fastcall` canonical Huffman symbol table builder. |
| `sub_006d3cd0` | `0x006d3cd0..0x006d3e11` | 322 B | 29 / 93 | `int __cdecl LZDecompress_Dispatch(const uint8_t *src, uint8_t *dst)` — dispatches `JDLZ` (`0x5a4c444a`) -> `sub_006cd550` and `HUFF` (`0x46465548`) -> `sub_006cd6a0`. |
| `sub_006d3e20` | `0x006d3e20..0x006d3f0c` | 237 B | 19 / 60 | `uint32_t __thiscall CIP_DecompressStream(void *this, const uint8_t *src, uint32_t src_size, uint8_t *dst, uint32_t dst_size)` — loops over 24-byte `0x55441122` (`CIP`) headers, invokes `sub_006d3cd0(cur + 24, dst + target_offset)` for each block, and terminates once the block with `target_offset == 0` completes. |

### 6.2 Complete Decoding & Verification of `CARS/240SX/TEXTURES.BIN`
- **Container Structure**: Version 8 TPK (`0xB3300000`, `421,248` bytes, SHA-256 `a0cf41f47e184f904a0020a3baf0e650f46f57e83b029bf812f5625786b3b61f`) using compressed `0x33310003` 24-byte entries (`name_hash, file_offset, compressed_size, uncompressed_size, flags, 0`) instead of `0x33310004`/`0x33310005`.
- **Decompressed Payload Layout**: Each entry decompresses via `sub_006d3e20` (`CIP`) into `pixel_bytes (size)` followed by a **148-byte trailer** at `uncompressed[uncompressed_size - 148 : uncompressed_size]` consisting of a standard 124-byte `0x33310004` texture record (`+0..+123`, with `35`-byte fixed name field at `+89..+123`) and a 24-byte `0x33310005` D3DFORMAT record (`+124..+147`).
- **Pixel-Exact Verification (`tools/validate_assets.py`, `experiments/recomp/verify_recomp.mjs`, `web/tests/browser.mjs`)**:
  - All 11 compressed textures in `CARS/240SX/TEXTURES.BIN` (plus `22` `DXT5` textures across the 3 `GLOBAL/` containers = **33 original textures total** in `assets.json` and `browser.json`, plus `1` `DXT3` texture in `GLOBAL/UniqueBootTextures.bin` = **34 textures verified against Pillow 13.0.0**) match 100% byte-for-byte between the lifted WebAssembly `sub_006d3e20`, the independent Python/TypeScript `cipDecompress` decoders, Pillow 13.0.0 DDS decoding (`max_diff == 0`), and headless Chrome WebGL2 `readPixels`:

| Index | Name (`0x33310004` Trailer) | Hash (`0x33310002`) | Dimensions | FourCC | Mips | Compressed -> Uncompressed | Base Level RGBA SHA-256 |
|---:|---|---|---|---:|---:|---:|---|
| 0 | `240SX_MISC` | `0x039cbe0b` | `512 × 256` | `DXT1` | 1 | `35,092 -> 65,684` B | `88c60acc70dac17bc8508c1d5de2ac8f61ac5f67e24ebcf189f22d70ad6e5355` |
| 1 | `240SX_BADGING_N` | `0x1b84caf8` | `256 × 256` | `DXT5` | 1 | `21,036 -> 65,684` B | `2d96eb0f5723c60a8f373b2b43114e01ce04da1e2e4ce2e54ed0d97d374dd744` |
| 2 | `240SX_ENGINE` | `0x4b6f3195` | `512 × 512` | `DXT1` | 1 | `97,052 -> 131,220` B | `c76d05e6b5da25d7155bccc5b5b4bca9bb3efba50a4f07ca4f486dd5f54f0243` |
| 3 | `240SX_KIT00_BRAKELIGHT_OFF` | `0x56ce1f7d` | `256 × 128` | `DXT1` | 1 | `9,504 -> 16,532` B | `830a17d14481e7b88c2c33b919c4d79c81ecb477c29d0d53f7e91daa75715eb2` |
| 4 | `240SX_WHEEL` | `0x77e8ad14` | `256 × 256` | `DXT3` | 1 | `25,244 -> 65,684` B | `84aa5ab02994433bd161f9b98dc08d4023aaabe161a12fb5dc8b2d635c5de8f0` |
| 5 | `240SX_INTERIOR` | `0xb316398b` | `512 × 512` | `DXT1` | 1 | `89,328 -> 131,220` B | `57303e64d6c42efd111763bc8f4d417f4b4afba74fb94206e531e84b1c049780` |
| 6 | `240SX_BADGING` | `0xb3dc27ab` | `256 × 256` | `DXT3` | 1 | `21,400 -> 65,684` B | `100c3d1d9e95d7129ea6bc4d6a2a84199ee1a1ff4b03c296f448c9ff668449e4` |
| 7 | `240SX_ENGINE_N` | `0xe401f762` | `512 × 512` | `DXT1` | 1 | `82,040 -> 131,220` B | `f367cac5dfa404da947b325c79db63b93fbf62596f84f8ae6a720402cd4e21b1` |
| 8 | `240SX_KIT00_BRAKELIGHT_GLASS_DAMAG`* | `0xe85318ea` | `256 × 128` | `DXT3` | 1 | `15,196 -> 32,916` B | `a369ddc0b5339fb9bfa0dce3bfa265aa1cd482dac71c4a0ad0f134c4bce888be` |
| 9 | `240SX_KIT00_BRAKELIGHT_ON` | `0xeb5b945f` | `256 × 128` | `DXT1` | 1 | `11,760 -> 16,532` B | `374a17c7b0dbccfbf872796b987e3b8a93dc66e98597b3abefc85734204bf7a5` |
| 10 | `240SX_KIT00_BRAKELIGHT_DAMAGE0` | `0xedd4b5d1` | `256 × 128` | `DXT1` | 1 | `12,412 -> 16,532` B | `a369ddc0b5339fb9bfa0dce3bfa265aa1cd482dac71c4a0ad0f134c4bce888be` |

*\*Note: `240SX_KIT00_BRAKELIGHT_GLASS_DAMAG` is stored truncated at 34 characters + NUL inside the 35-byte trailer name buffer; its hash `0xe85318ea` is the `bStringHash` of the full 36-character string `"240SX_KIT00_BRAKELIGHT_GLASS_DAMAGE0"`.*

### 6.3 `CARS/240SX/GEOMETRY.BIN` Chunk & Mesh Format (`tools/geometry.py`, `web/src/geometry.ts`)
Static disassembly of `sub_00457810` (`eSolid` loader at `VA 0x00457810..0x00457bd5`) and `sub_006ff240` (`eSolidPlatInfo` mesh loader at `VA 0x006ff240..0x006ff405`) in `nfs.exe`, validated against all `1,141` parts in `CARS/240SX/GEOMETRY.BIN` (`8,401,564` bytes, SHA-256 `4939ff6fb9dece2cefbfba2c0dcde2dc5efedcfbe9df16dc3ff83c591fa0fc8a`), established the complete vehicle geometry pipeline:
1. **Outer Container (`0x80134000`) & Directory (`0x80134001`)**:
   - `0x00134002` (`144` B): Header containing `part_count = 1,141` at `+12`.
   - `0x00134003` (`9,128` B): `1,141 × 8`-byte `(part_hash, 0)` table.
   - `0x00134004` (`27,384` B): `1,141 × 24`-byte `(part_hash, file_offset, compressed_size, uncompressed_size, flags, 0)` records.
   - Starting at `0x8f80` (immediately after `0x80134001`), each part record points to a `0x55441122` (`CIP`) multi-block stream that decompresses via the exact same `sub_006d3e20` (`CIP` + `JDLZ` + `HUFF`) pipeline into an `0x80134010` (`eSolid`) chunk.
2. **Decompressed `0x80134010` (`eSolid`) Structure**:
   - `0x00134011` (`eSolidPlatHeader`, 16-byte aligned payload `al = (chunk_pos + 0x17) & ~0x0f`):
     - `al + 0x10` (`u32`): `part_hash` (matches `bStringHash(name)`).
     - `al + 0x14` (`u16`): `num_tris`, `al + 0x18` (`u16`): `num_verts`.
     - `al + 0x20..0x2b` (`f32[3]`): `bbox_min`, `al + 0x30..0x3b` (`f32[3]`): `bbox_max`.
     - `al + 0x40..0x7f` (`f32[16]`): `4 × 4` transform matrix.
     - `al + 0xb8` (or `+0xac` / `+0xa0`): NUL-terminated ASCII part name (`"240SX_KIT00_BODY_A"`, etc.).
   - `0x00134012`: `N × 8`-byte `(texture_name_hash, 0)` table.
   - `0x00134013`: `M × 8`-byte `(light_material_hash, 0)` table (`PLASTIC`, `MAGSILVER`, `CHROME`, `CARSKIN`, etc.).
   - `0x00134015`: Shader sampler name table (`"DIFFUSE"`, `"NORMALMAP"`, `"AMBIENT"`).
   - `0x0013401a`: 16-byte aligned array of 80-byte `ePositionMarker` records (`hash, pad, f32[3] pos, f32[16] matrix`).
3. **Platform Mesh Container (`0x80134100`)**:
   - `0x00134900` (16-byte aligned `al = (q + 0x17) & ~0x0f`): `num_submeshes = u32(al + 16)`, `total_tris = u32(al + 40)`, `total_verts = u32(al + 48)`.
   - `0x00134b02` (128-byte aligned `al = (q + 0x87) & ~0x7f`): `num_submeshes × 128`-byte `eMeshEntry` descriptors:
     - `+0x00` (`u32`): `index_start` (in `uint16_t` indices into `0x00134b03`).
     - `+0x08..0x1b` (`i32[5]`): sampler slot mapping (`0 = DIFFUSE`, `1 = NORMALMAP`, `2 = AMBIENT`, `-1 = unused`).
     - `+0x1c..0x20` (`u8[5]`): texture indices into `0x00134012` (`0xff = unused`).
     - `+0x24` (`u32`): shader/material effect hash.
     - `+0x2c` (`u32`): `num_indices` (`num_triangles * 3`).
     - `+0x4c` (`u32`): `vertex_buffer_byte_size`.
     - `+0x52` (`u16 & 0x7fff`): `vertex_stride = 32` bytes.
   - `0x00134b01` (128-byte aligned `al = (q + 0x87) & ~0x7f`, one chunk per submesh): 32-byte `D3DDECLTYPE_SHORT4N` vertices:
     - `+0x00..0x07` (`i16[4]`): homogeneous position `(px, py, pz, pw)` where `pos = (px / pw, py / pw, pz / pw)` (`pw = 3277 ≈ 32767 / 10`), matching `0x00134011` `bbox_min..bbox_max` to 4 decimal places.
     - `+0x08..0x0b` (`i16[2]`): texture coordinates `(u, v) = (tu / 32767.0, tv / 32767.0)`.
     - `+0x0c..0x0f` (`u8[4]`): `D3DCOLOR` BGRA vertex color / ambient occlusion.
     - `+0x10..0x17` (`i16[4]`): unit normal vector `(nx, ny, nz, nw) / 32767.0`.
     - `+0x18..0x1f` (`i16[4]`): unit tangent vector `(tx, ty, tz, tw) / 32767.0`.
   - `0x00134b03` (32-byte aligned `al = (q + 0x27) & ~0x1f`): contiguous `uint16_t` triangle list index buffer (`GL_TRIANGLES`).

### 6.4 Unresolved External Dependencies & Limitations (Documented Explicitly)
1. **Shared Global Vehicle Textures (`GLOBAL/GLOBALB.LZC` & `CARSKIN`)**:
   - While 240SX-specific textures (`240SX_BADGING`, `240SX_MISC`, `240SX_INTERIOR`, `240SX_ENGINE`, `240SX_WHEEL`, `240SX_KIT00_BRAKELIGHT_*`) reside in `CARS/240SX/TEXTURES.BIN` and bind automatically in the 3D viewer when `TEXTURES.BIN` is loaded, vehicle submeshes also reference shared global texture hashes (`0x77a20245` `240SX_SKIN1`, `0x90e719eb` `DAMAGE_N`, `0xe5f6a5ed` `CHASSIS`, `0x027ff2dc` `BLACK`, `0xe4cea024` `TIRE_STYLE01`). Per `AGENTS.md`, no fallback or invented textures are substituted; the viewer shades unbound materials with hemisphere + two-light Lambertian + vertex AO and lists unresolved texture hashes in the metadata panel.
2. **Local-Origin Part Placement (`WHEEL`, `BRAKE`, `SEAT`)**:
   - All 27 exterior/chassis/engine/glass stock `240SX_KIT00_*_A` parts (`14,612` triangles) are authored directly in vehicle-space coordinates (`+X` forward, `+Y` left, `+Z` up) and assemble into the composite stock 240SX body in the viewer without invented transforms.
   - Reusable parts (`240SX_KIT00_WHEEL_TIRE_FRONT_A`, `240SX_KIT00_WHEEL_TIRE_REAR_A`, `240SX_KIT00_BRAKE_*`, `240SX_KIT00_SEAT_*`) are authored centered at local origin `[0, 0, 0]`; their 4-wheel/2-seat world transforms reside in VLT vehicle attributes (`ATTRIBUTES.BIN` / `FE_ATTRIB.BIN`) and attachment markers (`0x0013401a`). They can be inspected individually in the part selector with an explicit local-origin note.
