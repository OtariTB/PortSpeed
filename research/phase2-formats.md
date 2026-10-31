# Asset format discovery and validation — Phase 2

## Reference audit

These are community implementations/specifications, not official ProStreet format guarantees. Our bounded readers were authored for the subset validated below; no upstream tool binary, game machine code or decompressor blob is linked or executed.

| Reference | Revision / finding |
|---|---|
| [NFS-ModTools Version3Tpk](https://github.com/NFSTools/NFS-ModTools/blob/897c170eececb6f0f31c1925c2db4160d135c3b5/Common/Textures/Version3Tpk.cs) and [game dispatch](https://github.com/NFSTools/NFS-ModTools/blob/897c170eececb6f0f31c1925c2db4160d135c3b5/Common/ChunkManager.cs) | `897c170eececb6f0f31c1925c2db4160d135c3b5`; explicitly dispatches ProStreet to Version3Tpk. Reference for fields, not validation by itself. No root license file found; source not vendored into implementation. |
| [Explorer texture reader](https://github.com/nfs-tools/Explorer/blob/45e6fc4d4303669d4884cc5832aa24ef7275dd4e/texture_pack_stream.cpp) | `45e6fc4d4303669d4884cc5832aa24ef7275dd4e`; README actually checks only World support. Its texture structure is unsuitable for these ProStreet samples. No root license file found. |
| [xnfstpktool](https://github.com/xan1242/xnfstpktool/tree/bfd46d4e71df7a23db4f4e43c51aa37db2839fee) | Root MIT license, but its decompression header labels a machine-code blob as EA code distributed without permission. The implementation calls into that blob. Not used, built or executed. Its fetched reference cache was moved outside the repository/OneDrive to the local Phase 2 reference-quarantine directory; only empty directories remain in scratch. Do not treat a repository-level license as covering this blob. |
| [OpenSAGE BIG specification](https://github.com/OpenSAGE/Docs/blob/master/file-formats/big/index.rst) | Mixed-endian header and entry-table reference, accessed 2026-10-30; local samples expose an extra trailer not described there. |
| [OpenNFSTools JDLZ](https://github.com/MWisBest/OpenNFSTools/blob/master/LibNFS/Compression/JDLZ.cs) | Header reference, accessed 2026-10-30; payload decompressor not implemented or imported. |
| [Microsoft block compression](https://learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression) | BC3/DXT5: 4×4 blocks, RGB565 endpoints and color selectors, separate alpha endpoints/selectors. Used for authored Python and WASM decoders. |

Reference checkouts are ignored under `scratch/`, not dependencies or distributable project source. No clean-room claim is made: format reader source was reviewed. The CompLib GitHub URL guessed from a package name did not exist; no compression implementation was obtained that way.

## Implemented TPK subset

All numeric fields below are little-endian. Chunks are `(u32 id, u32 payload_length)`; the length excludes the 8-byte header. The high bit marks a parent chunk. The parser walks parent-bounded records, not byte-pattern searches. Input limit: 64 MiB, nesting 16, chunks 100,000, textures 4,096, dimensions at most 4,096 each. These are explicit research limits, not claims about game maxima.

Supported files contain exactly one `0xB3300000` root with metadata and pixel-data containers. Zero-ID chunks are skipped by their bounded length. Unknown bounded chunks are not given semantics. Duplicate metadata IDs, missing records, nonversion-8 info, compressed per-texture records, malformed strings and unconsumed records are rejected.

| Chunk | Validated interpretation |
|---|---|
| `0x33310001` | 124-byte pack info; first u32 is 8. Remaining fields are not required by this reader. |
| `0x33310002` | 8-byte hash records; size divided by 8 gives texture count. First u32 of each must match the corresponding texture record; second u32 remains uninterpreted. |
| `0x33310004` | Variable-length texture records; fixed 88 bytes, then one-byte name-field length, then padded ASCII name. |
| `0x33310005` | 24 bytes per texture; FourCC at record offset 12. Other fields remain uninterpreted. |
| `0x33320002` | Exactly 120 leading `0x11` bytes in this supported variant, then pixel-data base. Texture offsets are relative to that base. |
| `0x33310003` | Compressed per-texture descriptors. Detected and explicitly unsupported. |

Texture-record offsets relative to the start of its fixed fields:

| Offset | Type | Interpretation / checks |
|---:|---|---|
| 12 | u32 | Texture hash, matches indexed hash |
| 20 | u32 | Relative image offset, bounded inside pixel chunk |
| 24 | u32 | Palette placement; only `0xffffffff` supported |
| 28 | u32 | Total image bytes, must equal calculated mip-chain size |
| 32 | u32 | Palette size; must be zero |
| 36 | u32 | Base image bytes, must equal block-size calculation |
| 40 / 42 | u16 / u16 | Width / height |
| 46 | u8 | Image compression: `0x22/0x24/0x26` must match `DXT1/3/5` |
| 50 | u8 | Mip-level count, bounded by dimensions |
| 88 | u8 | Name-field byte count, includes NUL/padding |
| 89 | bytes | ASCII name, NUL terminated with zero remainder |

Other record fields are intentionally uninterpreted. Texture byte ranges cannot overlap. BC1/DXT1 and BC2/DXT3 size metadata can be recognized, but only BC3/DXT5 pixels are decoded, tested on original files, or displayed. Mip-chain bounds and total sizes are validated; only the base level is decoded for comparison/display. The original corpus includes mip counts 1, 3, 4, 6 and 7. Lower mip pixels have not been independently compared. Multiple mip levels and partial blocks also have synthetic tests.

## Concrete original-file evidence

`GLOBAL/LOADINGTEXTURES.BUN` has SHA-256 `a0213d5af6b4a828af80973bb408c9b9d97f09ce5526cfe7376178d3942ecd40` and 175,616 bytes.

- Root payload length: 175,608; root ends exactly at EOF.
- Info chunk header at `0x48`; hash chunk at `0xcc`, with 120 bytes → 15 textures.
- Texture records: `0x154..0x768`; format chunk header `0x768`, 360 bytes → 15 format records.
- Pixel chunk header `0x980`, payload `0x988`; validated 120-byte prefix yields data base `0xa00`.
- `ICON_STAR`: record `0x3c8`, hash `0x86bd8901`, 64×64, one mip, DXT5. Relative pixel offset `0xd000`, absolute `0xda00`, length 4,096, end `0xea00`. This is exactly 16×16 BC3 blocks × 16 bytes.

Cross-file validation also succeeded for `GLOBAL/UniqueBootTextures.bin` (3 textures, 702,720 bytes) and `GLOBAL/NISOverlayTextures.bin` (4 textures, 274,176 bytes). All **22 textures** satisfy record, hash-table, pixel-format, size, count and boundary checks. Full source hashes and offsets are in `local/phase2/assets.json`.

The proprietary selected PNG and DDS are local-only at `%LOCALAPPDATA%/NFSProStreetResearch/phase2/icon-star.png` and `icon-star.dds`. The texture is white artwork with variable alpha; viewing it on white hides its shape. The checkerboard browser view makes its alpha visible. No game asset is bundled in the web project.

## Independent decode validation

For each of those 22 textures:

1. Python parses the original pack and decodes its original BC3 base-level bytes into RGBA.
2. An authored standard DDS header wraps the same original blocks in memory. Pillow 13.0.0 independently decodes that DDS; every RGBA byte agrees with the Python decoder.
3. The browser independently parses the pack in TypeScript and decodes the blocks using compiled AssemblyScript WebAssembly; its RGBA SHA-256 agrees.
4. WebGL2 uploads the RGBA texture and draws it. `readPixels`, with rows reversed to top-down, matches that same hash, including alpha. This tests channel order, orientation, upload and rendering.

Selected RGBA SHA-256: `54b4be9413298327555a3b1005defa66cb11672e5fb9a0d373c8547fd0e1f5e7`. The PNG was read back with Pillow and equals the original decoded RGBA. These checks support this texture-layout subset and BC3 decoding, not full ProStreet material rendering or authenticity of the entire installation. No in-game screenshot comparison was performed.

## Other candidates and deliberate rejections

`CARS/240SX/TEXTURES.BIN` contains 11 hash entries and 11 24-byte compressed descriptors. The first observed descriptor names hash `0x039cbe0b`, absolute offset `0x58180`, compressed length 35,092 and advertised output length 65,684. At that location is `22 11 44 55` (LE `0x55441122`), with `JDLZ` at +24. This supports the CIP/JDLZ research lead; block ordering and decoded record trailers are not validated. The parser rejects this pack rather than fabricating geometry or pixels.

`FRONTEND/FRONTDLC.BUN` and `GLOBAL/GLOBALA.BUN` contain more than one root chunk and are rejected by the current standalone-pack contract. This is an implementation scope limit, not evidence of corrupt originals.

All five `.lzc` files have the checked `JDLZ 02 10 00 00` prefix and a little-endian input-length field equal to file size. Their advertised output sizes are 15,260,672; 13,985,024; 12,417,268; 642,824; and 1,472,384 bytes respectively (paths in `archives.json`). No payload decompression has been validated.

The three speech `.big` files match `BIG4`, little-endian total size and big-endian count/index-offset fields. Each advertises 250 entries; a bounded traversal ends at `0x17a6`, while the header says `0x17ae`. The intervening eight bytes are `4c 32 38 32 15 05 00 00` (`L282` prefix). Their meaning is unknown. `big4_index` rejects the unverified trailer; it does not silently reinterpret it or extract speech. This is a documented disagreement with the generic reference, not a validated full BIG4 variant implementation.

Next useful work: isolate root TPKs in multi-container bundles while preserving absolute offsets, then implement and independently validate CIP/JDLZ on the small car texture candidate. Physics, vehicle rendering, track streaming and gameplay remain out of scope.
