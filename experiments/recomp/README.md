# Experimental Static Recompilation Workspace (Phase D & Phase 3A)

This directory contains an isolated static recompilation pipeline for **Need for Speed: ProStreet** (`nfs.exe`). It translates original x86 functions from `.text` into C99 (`prostreet_lifted.c`) and WebAssembly (`prostreet_lifted.wasm`), verified against independent decoders and real vehicle texture/geometry streams.

## Architecture & Source-Protection Discipline

Per [`AGENTS.md`](../../AGENTS.md):
- The protected game directory is opened **read-only** after verifying the exact `nfs.exe` SHA-256 (`ee8a71c7c1e42923deb728e39a89317645cbcf26fc87cc48d3e07ade4dce2f72`).
- No original executable bytes or lifted/decompiled game functions are stored inside this repository or OneDrive workspace.
- Generated C99 (`prostreet_lifted.c`), AssemblyScript (`prostreet_lifted.ts`), and compiled WebAssembly (`prostreet_lifted.wasm`) outputs are written exclusively to `%LOCALAPPDATA%/NFSProStreetResearch/phase3/recomp`.
- Verification metadata is written to gitignored `research/local/phase3/recomp-verification.json`.

## Lifted Target Functions (`nfs.exe`, 11 Functions, `4,407` B `.text`, `1,518` Instructions)

| Symbol | VA Range | Bytes | Basic Blocks | Instructions | Signature / Semantics |
|---|---|---:|---:|---:|---|
| `sub_00436680` | `0x00436680..0x004366a7` | 40 | 5 | 18 | `uint32_t __cdecl bStringHash(const char *str)` — EA Black Box mul-33 (`h = h * 33 + c`) string hash starting at `0xffffffff`. |
| `sub_004366b0` | `0x004366b0..0x004366d7` | 40 | 5 | 18 | `uint32_t __cdecl bStringHashInit(const char *str, uint32_t init_hash)` — chained string hash. |
| `sub_004366e0` | `0x004366e0..0x00436713` | 52 | 6 | 23 | `uint32_t __cdecl bStringHashUpper(const char *str)` — case-insensitive uppercase string hash. |
| `sub_006cd550` | `0x006cd550..0x006cd69c` | 333 | 27 | 114 | `int __cdecl LZDecompress_JDLZ(const uint8_t *src, uint8_t *dst)` — ProStreet's native `JDLZ` (`0x5a4c444a`) LZ77 decompressor. |
| `sub_006cd6a0` | `0x006cd6a0..0x006cd6f8` | 89 | 6 | 30 | `uint32_t __cdeclLZDecompress_HUFF(const uint8_t *src, uint8_t *dst)` — ProStreet's native `HUFF` (`0x46465548`, version `1`) wrapper validating the 16-byte header and delegating to `sub_006cfc10`. |
| `sub_006cfc10` | `0x006cfc10..0x006d07b5` | 2,982 | 190 | 1,037 | `int __cdecl HUFF_DecodeBody(const uint8_t *src, uint8_t *dst, int comp_size, int uncomp_size)` — EA RefPack canonical Huffman + RLE + delta (`0x30fb`/`0x32fb`/`0x34fb`/`0xb0fb`/`0xb2fb`/`0xb4fb`) decompressor. |
| `sub_006cfbc0` | `0x006cfbc0..0x006cfc0c` | 77 | 3 | 32 | `__fastcall` Exp-Golomb variable-length bit reader helper used by `sub_006cfc10`. |
| `sub_006cfb40` | `0x006cfb40..0x006cfbb3` | 116 | 3 | 47 | `__cdecl` bitstream refills / alignment helper for `sub_006cfc10`. |
| `sub_006cfac0` | `0x006cfac0..0x006cfb36` | 119 | 5 | 46 | `__fastcall` canonical Huffman symbol table initialization helper for `sub_006cfc10`. |
| `sub_006d3cd0` | `0x006d3cd0..0x006d3e11` | 322 | 29 | 93 | `int __cdecl LZDecompress_Dispatch(const uint8_t *src, uint8_t *dst)` — magic-dispatching single-block decompressor (`JDLZ`, `HUFF`, `COMP`, `RAWW`, `REF`). |
| `sub_006d3e20` | `0x006d3e20..0x006d3f0c` | 237 | 19 | 60 | `uint32_t __thiscall CIP_DecompressStream(void *this, const uint8_t *src, uint32_t src_size, uint8_t *dst, uint32_t dst_size)` — multi-block `CIP` (`0x55441122`) stream decompressor. |

## Usage

1. **Lift `nfs.exe` functions to C99 and compile to WebAssembly**:
   ```powershell
   python experiments/recomp/lift_x86.py
   ```
2. **Run WebAssembly verification against 33 original texture hashes, all 11 compressed 240SX textures (`CARS/240SX/TEXTURES.BIN`), and 12 stock 240SX vehicle geometry streams (`CARS/240SX/GEOMETRY.BIN`)**:
   ```powershell
   node experiments/recomp/verify_recomp.mjs
   ```
3. **Run synthetic unit tests (including malformed instructions and path-containment guards)**:
   ```powershell
   python -m unittest discover -s tests -v
   ```
