# Phase 2 result and reproducible commands

Date: 2026-10-30, Asia/Tbilisi. All work is local; nothing was deployed or published.

**A real ProStreet installation texture now passes through a validated container reader, an authored WebAssembly BC3 decoder, and WebGL2.** The selected example is `ICON_STAR` from `GLOBAL/LOADINGTEXTURES.BUN`. This is an asset-pipeline proof of concept, not a reconstructed engine or gameplay implementation.

## Implemented and verified

- Three executable variants identified with hashes, PE metadata and static version-resource checks. User confirms the top-level `nfs.exe` is used; clean retail v1.1 remains unverified. See [executable findings](phase2-executables.md).
- Bounded Python and TypeScript standalone version-8 TPK readers. Exact format support and unknown fields are documented in [format findings](phase2-formats.md).
- Authored Python BC3 decoder, DDS wrapper and PNG writer. Pillow 13.0.0 independently agrees byte-for-byte on all 22 original DXT5 textures across three packs.
- Actual compiled WebAssembly BC3 decoding via AssemblyScript 0.28.20. The host validates files in TypeScript; it does not pretend the TPK parser or entire engine runs in WASM. The decoder is compiled from authored source and can later be replaced behind the same byte-buffer interface.
- Vite 8.3.5 / TypeScript 7.0.2 frontend; WebGL2 texture upload/draw, alpha checkerboard, texture selection, metadata/hash display, size caps, unsupported-file errors and GPU-context error reporting.
- Headless Chrome 156.0.8078.74, forced SwiftShader software WebGL2: all 22 original textures match Python/Pillow hashes after WASM decoding **and framebuffer readback**. This verifies rendering correctness for these samples, not hardware performance or all browsers. Browser test also checks invalid input clears the old asset, no page errors, and only loopback GET requests.
- 23 Python unit tests (including the original 6 PE/recon tests), 5 TypeScript/WASM tests. Cases cover every truncation of a synthetic pack, parent bounds, counts, hashes, name bounds, dimensions, formats, overlapping texture ranges, mip lengths, BC3 alpha modes, partial blocks, BIG4 bounds and JDLZ headers. Fixtures contain only authored synthetic bytes.
- Production build passes. The app contains no original assets. Generated decoded PNG/DDS and browser screenshot reside only in `%LOCALAPPDATA%/NFSProStreetResearch/phase2`.
- A second complete 3,362-file inventory rehashed every file. Compared with Phase 1: no files added/removed, no SHA-256/size/mtime differences, no read errors, no skips, all reads metadata-stable. Original installation content remains unchanged.

## Explicit limits

No gameplay, physics, vehicle geometry, track rendering, original shaders, streaming system, sound decoder, C++ game engine, or executable translation is implemented. `engine/` is only a reserved directory. No game executables or bundled scripts were run; no Ghidra import was needed.

CIP/JDLZ car-pack decoding and multi-root BUN selection remain unsupported. JDLZ header validation does not validate decompressed content. The generic BIG4 reader deliberately fails on the speech archives' unknown eight-byte index trailer. DXT1/DXT3 metadata is recognized but their pixel decoders are absent. Base mip rendering does not reproduce original texture filtering, materials or lighting. No unrelated substitute assets are used.

The native engine's long-term language remains open. AssemblyScript was chosen for this narrow decoder because Node/npm were verified and it produces standalone WASM without first installing Emscripten. It is not an engine-language decision or a performance claim.

## Setup and execution (PowerShell, repository root)

Existing `config/local.json` supplies the original game root; use `config/local.example.json` on another machine. Never put assets under `web/public/`.

```powershell
# Static executable identification and all Python tests (standard library):
powershell -NoProfile -File tools/identify_executables.ps1
python -m unittest discover -s tests -v

# Inspect supported texture metadata or other archive candidates without extraction:
python tools/inspect_tpk.py 'Need For Spped - Pro Street/GLOBAL/LOADINGTEXTURES.BUN'
python tools/inspect_archives.py

# Optional isolated independent image validation (Python 3.13 verified here):
py -3.13 -m venv scratch/validation-env
scratch/validation-env/Scripts/python.exe -m pip install Pillow==13.0.0
scratch/validation-env/Scripts/python.exe tools/validate_assets.py

# Install exact browser dependencies and compile/test:
npm --prefix web ci --ignore-scripts
npm --prefix web test
npm --prefix web run build

# Browser integration test (requires installed Google Chrome and Python report):
npm --prefix web run test:browser

# Interactive viewer (keep this process open while using the page):
npm --prefix web run dev
```

Open the printed loopback URL, normally `http://127.0.0.1:5173`. Choose the original `GLOBAL/LOADINGTEXTURES.BUN`; the viewer selects `ICON_STAR`. File selection uses browser-local bytes, not an upload. Select another texture using the dropdown. Stop the server with Ctrl+C. The automated QA server was stopped after testing.

To repeat full source-integrity verification, choose a fresh output directory:

```powershell
python tools/recon.py --hash-all --output research/local/phase2/another-inventory
python tools/compare_inventory.py research/local/inventory/inventory.json research/local/phase2/another-inventory/inventory.json
```

## Evidence locations

Ignored `research/local/phase2/` contains `executables.json`, `executable-sections.json`, `assets.json`, `archives.json`, `browser.json`, `integrity.json` and `final-inventory/`. Raw reports are local research material and must not be published indiscriminately. Exact reference revisions and source links are in [phase2-formats.md](phase2-formats.md).

Local-only outputs: `icon-star.png`, `icon-star.dds`, and `browser-icon-star.png` under `%LOCALAPPDATA%/NFSProStreetResearch/phase2`. That location also quarantines a fetched reference checkout containing an explicitly labelled proprietary decompressor blob; none of its code is used or executed. The original game installation was never modified. Git ignores local reports, dependency/reference checkouts, generated builds and common original-asset extensions, but ignore rules are not a substitute for reviewing commits.

Next milestone: support selecting validated TPK roots inside multi-container BUNs, then independently validate CIP/JDLZ on the car texture candidate. Establish trustworthy v1.1 executable provenance before address-based engine reconstruction.
