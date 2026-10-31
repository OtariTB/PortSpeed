# PortSpeed

> **Experimental native browser port of Need for Speed: ProStreet (2007) using x86 static recompilation and WebAssembly.**

---

## Legal & Research Disclaimer

**PortSpeed is an independent reverse-engineering and preservation research project.**
- This project is **not** affiliated with, sponsored by, or endorsed by Electronic Arts, EA Black Box, or their licensors.
- "Need for Speed" and "Need for Speed: ProStreet" are trademarks of Electronic Arts Inc.
- **No copyrighted game assets, proprietary binaries, or original game code are distributed in this repository.** Users must supply their own legally purchased copy of *Need for Speed: ProStreet* (PC v1.1).

---

## Project Objective & Architecture

PortSpeed investigates bringing original 2007 PC Windows x86 games to modern web browsers through **static binary recompilation** rather than emulation, VM virtualization, or manual gameplay reimplementation:

1. **Preserve Original Logic**: Rather than reimplementing physics or gameplay logic from scratch, the original MSVC 8.0 x86 machine code in `nfs.exe` is translated ahead-of-time (AOT) to C99 and WebAssembly.
2. **1:1 Guest Linear Memory**: Guest virtual addresses (`0x00400000..0x01010000`) map directly into WebAssembly linear memory (`IMAGE_BASE=0`), eliminating pointer translation overhead for memory access.
3. **Native Asset Pipeline**: Original compressed texture containers (`.BUN`/`.BIN`) and 3D vehicle geometries (`GEOMETRY.BIN`) are decoded locally via native and lifted WebAssembly routines and rendered using WebGL2.
4. **Strict Source-Protection Discipline**: All game files are opened strictly read-only. Proprietary decompiled outputs, raw game dumps, and generated binaries are kept outside Git and OneDrive under `%LOCALAPPDATA%/NFSProStreetResearch/`.

---

## Current Status & Limitations

> [!WARNING]
> **PortSpeed is an early-stage research prototype. The game is NOT playable yet.**
> There is currently no game loop, physics engine, sound playback, or input handling running in the browser.

### Completed Milestones

- [x] **Phase 1: Read-Only Reconnaissance**:
  - Validated inventory scanner across `3,362` original installation files (`5.6 GB`).
  - PE32 inspection of all executables (`nfs.exe`, `nfs.exe.org`, ViTALiTY v1.1).
- [x] **Phase 2: Texture Decoding & WebGL2 Viewer**:
  - Implemented AssemblyScript WebAssembly BC1 (`DXT1`), BC2 (`DXT3`), and BC3 (`DXT5`) decoders.
  - Verified **34 original game textures** with 100% pixel-exact parity (`max_diff == 0`) against Pillow DDS decoding and WebGL2 `readPixels`.
- [x] **Phase 3A: Static Lifter & Vehicle Asset Pipeline**:
  - Located and disassembled the original game's `HUFF` (`0x46465548`), `JDLZ` (`0x5a4c444a`), and `CIP` (`0x55441122`) decompression pipeline in `nfs.exe`.
  - Extended the x86 lifter (`experiments/recomp/lift_x86.py`) to lift 11 decompression functions (`4,407` bytes `.text`, `1,518` instructions) to C99 and WebAssembly (`prostreet_lifted.wasm`).
  - Verified full in-place decompression of `CARS/240SX/TEXTURES.BIN` (all 11 compressed textures) and `CARS/240SX/GEOMETRY.BIN` (all 1,141 `eSolid` parts).
  - Built an isolated WebGL2 3D mesh viewer with orbit camera and stock 240SX vehicle-space assembly (`14,612` triangles).
- [x] **Phase 3B: Guest Memory Loader & Static C++ Initializer Proof of Concept**:
  - Implemented bounds-checked PE section memory loader (`experiments/recomp/guest_memory.py`) mapping `.rdata` and `.data` into WebAssembly linear memory.
  - Implemented indirect guest call dispatcher `callGuestFunction(funcVa)`.
  - Successfully lifted and executed genuine static C++ initializer **`sub_00959ca0` (`_initterm` slot 45)** in WebAssembly, verifying correct return value, stack balance, callee-saved register preservation, and observable `.data` linked-list registration.

---

## Repository Structure

```
├── .gitignore                     # Comprehensive exclusions for proprietary/local assets
├── AGENTS.md                      # Strict source protection and reverse-engineering rules
├── README.md                      # Project overview and instructions
├── config/
│   └── local.example.json         # Example path configuration
├── experiments/
│   └── recomp/                    # Static recompilation pipeline (lifter, WASM, tests)
│       ├── guest_memory.py        # Checked guest PE memory loader
│       ├── lift_x86.py            # Static x86 -> C99 / AssemblyScript lifter
│       ├── test_initializer.mjs   # Test executing genuine static initializer in WASM
│       ├── verify_recomp.mjs      # Cross-validation against game assets
│       └── x86_cpu.h              # C99 x86 CPU emulation state struct
├── research/
│   ├── PROJECT_STATUS.md          # Comprehensive technical status and roadmap
│   ├── findings.md                # Reverse-engineering discoveries
│   ├── phase2-executables.md      # Executable analysis and PE reports
│   ├── phase2-formats.md          # Texture container & format documentation
│   └── phase3-recompilation.md    # Static recompilation architecture & decompression
├── tests/                         # Synthetic Python unit tests (37 tests)
├── tools/                         # Static analysis, inspection, and geometry parsers
└── web/                           # TypeScript / Vite / WebGL2 browser application
    ├── assembly/bc3.ts            # AssemblyScript DXT1/DXT3/DXT5 decoder
    ├── src/
    │   ├── geometry.ts            # Geometry container parser
    │   ├── main.ts                # Texture viewer & 3D vehicle lab UI
    │   ├── mesh_renderer.ts       # WebGL2 3D orbit mesh renderer
    │   └── tpk.ts                 # TPK container and decompression routines
    └── tests/                     # Playwright browser integration & unit tests
```

---

## Getting Started

### Prerequisites

- **Python 3.10+** (standard library only for core tools; `capstone` and `pillow` for asset/disassembly validation).
- **Node.js 18+** & **npm**.
- A legally acquired PC installation of **Need for Speed: ProStreet v1.1**.

### Setup Configuration

Copy the example configuration and set your installation directory:

```powershell
cp config/local.example.json config/local.json
```

Edit `config/local.json`:
```json
{
  "game_root": "C:\\Games\\Need for Speed ProStreet"
}
```

*(Note: `config/local.json` is strictly gitignored to protect user-local paths).*

---

## Running Tests

### 1. Python Unit Tests (37 tests)
Runs synthetic fixtures for archive parsers, geometry containers, PE memory loader, and x86 lifter:
```powershell
python -m unittest discover -s tests -v
```

### 2. Static Recompilation Initializer Test
Tests loading PE sections into guest memory and executing `sub_00959ca0` in WebAssembly:
```powershell
node experiments/recomp/test_initializer.mjs
```

### 3. Static Recompilation Full Asset Verification
Validates 11 lifted decompression functions against 33 textures and 12 vehicle geometry streams:
```powershell
node experiments/recomp/verify_recomp.mjs
```

### 4. Web Unit & Production Build
Compiles AssemblyScript decoders and runs web test suite:
```powershell
npm --prefix web test
npm --prefix web run build
```

### 5. Playwright WebGL2 Browser Integration Tests
Verifies texture readback and 3D vehicle rendering in headless Chrome WebGL2:
```powershell
npm --prefix web run test:browser
```

---

## Running the Interactive Web Lab

To interactively view decoded textures and 3D vehicle geometries:

```powershell
npm --prefix web run dev
```

Open the printed localhost URL (`http://127.0.0.1:5173/`):
- **Texture Container Panel**: Select `GLOBAL/LOADINGTEXTURES.BUN` or `CARS/240SX/TEXTURES.BIN` to inspect decoded DXT1/DXT3/DXT5 textures.
- **3D Vehicle Geometry Lab**: Select `CARS/240SX/GEOMETRY.BIN` to view the composite stock 240SX body or any of the 1,141 individual `eSolid` parts with the WebGL2 orbit camera.

---

## Instructions for Resuming Development

When resuming static recompilation:
1. Consult [`research/PROJECT_STATUS.md`](research/PROJECT_STATUS.md) for the prioritized execution roadmap and remaining blockers.
2. Review [`AGENTS.md`](AGENTS.md) for strict source protection and read-only game directory constraints.
3. The next recommended milestone is lifting the remaining leaf initializers in `_initterm` and implementing `atexit` list dispatching to boot past C++ static initialization.
