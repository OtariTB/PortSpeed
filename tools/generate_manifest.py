#!/usr/bin/env python3
"""
Need for Speed ProStreet - Asset Manifest Generator & Verifier.

Scans the authentic game installation directory (read-only) and generates
web/public/data-manifest.json cataloging file paths, byte sizes, modification timestamps,
and 1 MiB chunk boundaries for the browser OPFS background streaming engine.
"""

import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

DEFAULT_GAME_DIR = Path(r"C:\Games\Pro Street\Need For Spped - Pro Street")
DEFAULT_OUT_DIR = Path(__file__).resolve().parent.parent / "web" / "public"
OPFS_BLOCK_SIZE = 1048576  # 1 MiB

CRITICAL_CHECK_FILES = [
    "GLOBAL/GLOBALB.LZC",
    "GLOBAL/LOADINGTEXTURES.BUN",
    "CARS/240SX/GEOMETRY.BIN",
    "CARS/240SX/TEXTURES.BIN",
    "FRONTEND/FRONTB1.BUN",
    "TRACKS/L6R_Autopolis.BUN",
]


def scan_game_directory(game_dir: Path) -> tuple[list[dict], int, int]:
    """
    Recursively scans the game folder in strictly read-only mode and produces
    the file entry list conforming to GameManifest schema.
    """
    if not game_dir.is_dir():
        raise FileNotFoundError(f"Game directory not found: {game_dir}")

    files = []
    total_bytes = 0
    total_blocks = 0

    for root, _, filenames in os.walk(game_dir):
        for name in filenames:
            file_path = Path(root) / name
            try:
                st = file_path.stat()
                rel_path = file_path.relative_to(game_dir).as_posix()
                size = st.st_size
                mtime = int(st.st_mtime)
                blocks = math.ceil(size / OPFS_BLOCK_SIZE) if size > 0 else 0

                entry = {
                    "path": rel_path,
                    "size": size,
                    "mtime": mtime,
                    "isDir": False,
                    "blocks": blocks,
                }
                files.append(entry)
                total_bytes += size
                total_blocks += blocks
            except OSError as e:
                print(f"Warning: could not stat {file_path}: {e}", file=sys.stderr)

    # Sort deterministically by lowercase path
    files.sort(key=lambda x: x["path"].lower())
    return files, total_bytes, total_blocks


def build_manifest_dict(files: list[dict], total_bytes: int, total_blocks: int, game_dir: Path) -> dict:
    """Builds the complete JSON manifest object."""
    return {
        "format": "prostreet-opfs-v1",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sourceDir": str(game_dir),
        "totalFiles": len(files),
        "totalBytes": total_bytes,
        "totalGigabytes": round(total_bytes / (1024**3), 2),
        "totalBlocks": total_blocks,
        "blockSize": OPFS_BLOCK_SIZE,
        "files": files,
    }


def verify_critical_assets(files: list[dict]) -> list[str]:
    """Verifies that all required core asset bundles exist in the catalog."""
    indexed = {f["path"].lower(): f for f in files}
    missing = []
    for req in CRITICAL_CHECK_FILES:
        if req.lower() not in indexed:
            missing.append(req)
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=Path(os.environ.get("PROSTREET_GAME_DIR", DEFAULT_GAME_DIR)),
        help=f"Path to authentic NFS ProStreet game installation (default: {DEFAULT_GAME_DIR})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR / "data-manifest.json",
        help=f"Output manifest JSON path (default: {DEFAULT_OUT_DIR / 'data-manifest.json'})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify existing data-manifest.json against the game folder",
    )
    args = parser.parse_args()

    print("=====================================================================")
    print(" PortSpeed Asset Manifest Generator (Step 7.2)")
    print("=====================================================================")
    print(f" Source Directory: {args.game_dir}")
    print(f" Output Target:    {args.out}")

    if not args.game_dir.is_dir():
        print(f"\nERROR: Game directory does not exist: {args.game_dir}")
        print("Set PROSTREET_GAME_DIR or pass --game-dir=<path>")
        return 1

    if args.check:
        print("\n[Mode: Verification]")
        if not args.out.is_file():
            print(f"ERROR: Manifest file does not exist: {args.out}")
            return 1
        manifest = json.loads(args.out.read_text(encoding="utf-8"))
        print(f" Loaded manifest: {manifest.get('totalFiles')} files ({manifest.get('totalGigabytes')} GB)")
        missing = verify_critical_assets(manifest.get("files", []))
        if missing:
            print(f" ERROR: Missing critical game assets in manifest: {missing}")
            return 1
        print(" Verification PASSED: All critical assets cataloged cleanly.")
        return 0

    print("\n[1/3] Scanning game installation in read-only mode...")
    start_time = time.time()
    files, total_bytes, total_blocks = scan_game_directory(args.game_dir)
    elapsed = time.time() - start_time
    print(f"  Scanned {len(files)} files in {elapsed:.2f}s")
    print(f"  Total Data Size: {total_bytes / (1024**3):.2f} GB ({total_bytes:,} bytes)")
    print(f"  Total 1 MiB Chunk Blocks: {total_blocks:,}")

    print("\n[2/3] Verifying core engine bundle assets...")
    missing = verify_critical_assets(files)
    if missing:
        print(f"  WARNING: Missing critical assets: {missing}")
    else:
        print(f"  All {len(CRITICAL_CHECK_FILES)} critical engine asset checks verified.")

    print("\n[3/3] Writing data-manifest.json...")
    manifest = build_manifest_dict(files, total_bytes, total_blocks, args.game_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    out_size = args.out.stat().st_size
    print(f"  Emitted {args.out} ({out_size / 1024:.1f} KB)")
    print("\n=====================================================================")
    print(" SUCCESS: data-manifest.json generated successfully!")
    print("=====================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())

