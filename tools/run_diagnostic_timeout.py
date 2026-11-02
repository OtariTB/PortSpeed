"""PortSpeed - Diagnostic Runner with Hard 60-Second Timeout.

Spawns the genuine WASM boot diagnostic under Node.js, captures real-time
progress logging, and enforces a strict 60-second execution deadline via taskkill.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_SCRIPT = ROOT / "tests" / "test_game_wasm.mjs"
TIMEOUT_SECS = 60.0


def main() -> int:
    cmd = ["node", "--experimental-wasi-unstable-preview1", str(TEST_SCRIPT)]
    print(f"=== PortSpeed Diagnostic Runner (Hard {int(TIMEOUT_SECS)}s Timeout) ===")
    print(f"Command: {' '.join(cmd)}")
    print(f"Working Directory: {ROOT}")
    print("-" * 60)
    sys.stdout.flush()

    env = dict(os.environ)

    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    lines: list[str] = []
    lock = threading.Lock()

    def reader() -> None:
        try:
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                with lock:
                    lines.append(line)
                sys.stdout.write(line)
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"[READER ERROR] {e}\n")
        finally:
            if proc.stdout:
                proc.stdout.close()

    t_thread = threading.Thread(target=reader, daemon=True)
    t_thread.start()

    start_time = time.time()
    timed_out = False

    while True:
        elapsed = time.time() - start_time
        ret = proc.poll()
        if ret is not None:
            break
        if elapsed >= TIMEOUT_SECS:
            timed_out = True
            break
        time.sleep(0.1)

    if timed_out:
        print(f"\n[TIMEOUT] Hard {TIMEOUT_SECS:.1f}s timeout expired! Forcing taskkill on PID {proc.pid}...")
        sys.stdout.flush()
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, text=True)
        except Exception as e:
            print(f"[KILL ERROR] {e}")
        try:
            proc.wait(timeout=5.0)
        except Exception:
            pass
        print(f"[TERMINATED] Child process {proc.pid} successfully killed.")
        sys.stdout.flush()
    else:
        print(f"\n[EXIT] Process exited with return code {proc.returncode} in {time.time() - start_time:.2f}s.")
        sys.stdout.flush()

    t_thread.join(timeout=2.0)

    # Analyze results
    print("\n" + "=" * 60)
    print("=== Diagnostic Execution Analysis ===")
    print("=" * 60)

    starts: list[tuple[int, str]] = []
    dones: list[tuple[int, str]] = []

    with lock:
        for l in lines:
            if "-> [START] Constructor #" in l:
                # format: -> [START] Constructor #170 (0x95aa60)...
                try:
                    part = l.split("-> [START] Constructor #")[1]
                    c_num = int(part.split()[0])
                    fn_va = part.split("(")[1].split(")")[0]
                    starts.append((c_num, fn_va))
                except Exception:
                    pass
            elif "<- [DONE]  Constructor #" in l:
                # format: <- [DONE]  Constructor #170 (0x95aa60)
                try:
                    part = l.split("<- [DONE]  Constructor #")[1]
                    c_num = int(part.split()[0])
                    fn_va = part.split("(")[1].split(")")[0]
                    dones.append((c_num, fn_va))
                except Exception:
                    pass
            elif "[PASS] Constructor #169 completed!" in l:
                dones.append((169, "0x95aa40"))

    if starts:
        last_start_num, last_start_va = starts[-1]
        print(f"Last Constructor Started : #{last_start_num} ({last_start_va})")
    else:
        last_start_num, last_start_va = 0, "none"
        print("Last Constructor Started : None (before #169)")

    if dones:
        last_done_num, last_done_va = dones[-1]
        print(f"Last Constructor Returned: #{last_done_num} ({last_done_va})")
    else:
        last_done_num, last_done_va = 0, "none"
        print("Last Constructor Returned: None")

    if last_start_num > last_done_num:
        print(f"[HANG DETECTED] Constructor #{last_start_num} ({last_start_va}) was entered but NEVER returned.")
    elif timed_out:
        print(f"[HANG DETECTED] Process timed out after {TIMEOUT_SECS}s at Constructor #{last_start_num}.")
    else:
        print("[COMPLETED] All started constructors returned.")

    print("=" * 60)
    sys.stdout.flush()

    return 1 if timed_out or (last_start_num > last_done_num) else 0


if __name__ == "__main__":
    sys.exit(main())
