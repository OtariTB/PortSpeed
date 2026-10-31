# Reconnaissance record — 2026-10-30 (Asia/Tbilisi)

Current work: [Phase 3 static recompilation analysis and proof of concept](phase3-recompilation.md), [Phase 2 results and commands](phase2-status.md), [executable identification](phase2-executables.md), and [format validation](phase2-formats.md).

Historical Phase 1: [findings.md](findings.md), [ghidra.md](ghidra.md) and [first-proof-of-concept.md](first-proof-of-concept.md). The following original record describes Phase 1 only; Phase 2 adds validated local texture extraction outside the workspace.

Local evidence (ignored by Git):

- `local/inventory/inventory.json`: all relative paths, sizes, SHA-256 hashes, first 32 bytes, PE headers and DLL import names.
- `local/inventory/summary.md`: extension totals, largest files, static dependencies and scan errors.
- `local/environment.json`: executable locations, actual version command output and exit codes.

The inventory is the authoritative record for this local snapshot. It covers the supplied outer folder, including support files and redistributables. It is not a manifest of a verified retail distribution. Reports contain diagnostic bytes and local paths; do not publish raw reports.

Repeat using the commands in the root README and a fresh output directory. No game binary was executed, patched, copied, extracted, or imported into a Ghidra project during this reconnaissance. Analysis reads do not intentionally alter game content or metadata; OS-managed access-time bookkeeping is outside the scanner's control.
