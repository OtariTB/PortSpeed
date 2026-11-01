#!/usr/bin/env python3
"""PortSpeed - Combined C99-to-WebAssembly Build Pipeline.

Compiles all 32 lifted x86 C99 shards, runtime compatibility layers,
dispatch table, and MSVCR80/Win32/D3D9 shims into a single WebAssembly module: build/game.wasm.
"""

import os
import sys
import time
import subprocess
import concurrent.futures
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIG_CC = ROOT / "tools" / "toolchain" / "zig" / "zig.exe"
OBJ_DIR = ROOT / "build" / "obj"
OUTPUT_WASM = ROOT / "build" / "game.wasm"

CFLAGS = [
    "-target", "wasm32-wasi",
    "-msimd128",
    "-mtail-call",
    "-O1",
    "-g0",
    "-Wno-c23-extensions",
    "-I.",
    "-Iruntime",
    "-Iinclude",
]

EXPORTS = [
    "boot_engine",
    "boot_get_status",
    "boot_reset_status",
    "boot_init_memory",
    "boot_bind_iats",
    "boot_install_hooks",
    "boot_run_initializers",
    "boot_setup_arguments",
    "boot_invoke_main",
    "initterm_run_cpp_constructors",
    "initterm_run_c_initializers",
    "initterm_install_hooks",
    "initterm_run_exit_destructors",
    "fntab_init",
    "guest_memory_init",
    "g_dtab",
    "dispatch_indirect",
    "sub_00828ebc",
    "sub_00828f01",
    "sub_00828652",
]

LDFLAGS = [
    "-target", "wasm32-wasi",
    "-mexec-model=reactor",
    "-Wl,--initial-memory=2c000000",   # 704 MB (0x2c000000)
    "-Wl,--max-memory=2c000000",
    "-Wl,--global-base=28000000",      # 640 MB (0x28000000) - places g_dtab & BSS above 640MB guest heap
    "-Wl,-z,stack-size=65536",          # 64 KB WASM stack in null-guard page
] + [f"-Wl,--export={exp}" for exp in EXPORTS]


def compile_file(src: Path, obj: Path) -> tuple[str, bool, float, str]:
    t0 = time.time()
    # Check cache: if obj exists and newer than src
    if obj.exists() and obj.stat().st_size > 0 and obj.stat().st_mtime >= src.stat().st_mtime:
        return src.name, True, 0.0, "cached"

    cmd = [str(ZIG_CC), "cc"] + CFLAGS + ["-c", str(src), "-o", str(obj)]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    dt = time.time() - t0
    if res.returncode != 0:
        return src.name, False, dt, res.stderr + res.stdout
    return src.name, True, dt, ""


def main():
    if not ZIG_CC.exists():
        print(f"[ERROR] Zig toolchain not found at: {ZIG_CC}")
        sys.exit(1)

    OBJ_DIR.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    # Collect source files
    runtime_sources = [
        ROOT / "runtime" / "memory.c",
        ROOT / "runtime" / "crt.c",
        ROOT / "runtime" / "win32.c",
        ROOT / "runtime" / "d3d9.c",
        ROOT / "runtime" / "initterm.c",
        ROOT / "runtime" / "boot.c",
        ROOT / "gen" / "fntab.c",
    ]

    shard_sources = sorted((ROOT / "gen").glob("shard_*.c"))
    all_sources = runtime_sources + shard_sources

    print(f"=== PortSpeed WebAssembly Build Pipeline ===")
    print(f"Toolchain:   Zig 0.13.0 (Clang 18 + wasm-ld)")
    print(f"Target:      wasm32-wasi (Musl libc)")
    print(f"Sources:     {len(all_sources)} compilation units ({len(runtime_sources)} runtime/fntab, {len(shard_sources)} shards)")
    print(f"Output:      {OUTPUT_WASM}")
    print(f"Concurrency: 4 parallel compilation workers")
    print("-" * 55)

    tasks = []
    for src in all_sources:
        obj = OBJ_DIR / (src.stem + ".o")
        tasks.append((src, obj))

    failed = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(compile_file, src, obj): src.name for src, obj in tasks}
        for fut in concurrent.futures.as_completed(futures):
            name, ok, dt, msg = fut.result()
            if not ok:
                print(f"[FAIL] {name:15} failed after {dt:.1f}s:\n{msg}")
                failed = True
            elif msg == "cached":
                print(f"[SKIP] {name:15} (cached)")
            else:
                print(f"[ OK ] {name:15} compiled in {dt:.1f}s")

    if failed:
        print("[ERROR] Compilation failed. Aborting link.")
        sys.exit(1)

    # Link phase
    print("-" * 55)
    print("Linking build/game.wasm...")
    t_link = time.time()

    all_objs = [str(OBJ_DIR / (src.stem + ".o")) for src in all_sources]
    link_cmd = [str(ZIG_CC), "cc"] + LDFLAGS + ["-o", str(OUTPUT_WASM)] + all_objs

    res = subprocess.run(link_cmd, cwd=str(ROOT), capture_output=True, text=True)
    t_link_elapsed = time.time() - t_link

    if res.returncode != 0:
        print(f"[ERROR] Linking failed after {t_link_elapsed:.1f}s:\n{res.stderr}\n{res.stdout}")
        sys.exit(1)

    wasm_size = OUTPUT_WASM.stat().st_size
    total_elapsed = time.time() - t_start

    print(f"[SUCCESS] Linked {OUTPUT_WASM.name} in {t_link_elapsed:.1f}s")
    print(f"Module Size:   {wasm_size:,} bytes ({wasm_size / (1024*1024):.2f} MB)")
    print(f"Total Time:    {total_elapsed:.1f}s")
    print("=============================================")


if __name__ == "__main__":
    main()
