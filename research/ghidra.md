# Ghidra headless reconnaissance

Verified locally: `Ghidra/application.properties` declares 12.2 PUBLIC, revision `8ca9077040cc43cd790babcfccf19475622a3e9a`, Java minimum 25. The installed Java 25 runtime meets that declared minimum. Both `support/analyzeHeadless.bat` and the bundled Markdown/HTML headless manuals exist.

Running `support/analyzeHeadless.bat` without arguments successfully reached the usage printer. It returned exit code 1 for the missing required project arguments, rather than a Java startup error. This is a launcher smoke check only; no project import, auto-analysis, or Ghidra script has been tested. The batch launcher defaults headless heap to 2 GB and supports `GHIDRA_HEADLESS_MAXMEM`.

The bundled manual and [upstream NSA headless documentation](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md) describe these capabilities:

- `-import` creates program records from files; `-process` operates on existing records.
- `-noanalysis` skips automatic analysis; pre/post scripts can still run.
- `-readOnly` discards program changes; it does not sandbox scripts or prohibit their filesystem writes.
- `-analysisTimeoutPerFile` bounds auto-analysis, not the whole invocation or every script.
- `-max-cpu` limits analysis concurrency; `-log` and `-scriptlog` select log files.

Consult the installed 12.2 manual before execution; upstream master may change. First future experiment should import one identified executable with `-noanalysis -readOnly`, independently confirm x86/PE sections/imports, then selectively analyze relevant asset-loader functions. Keep provenance labels attached to every address and hash. Avoid bulk recursive import and do not treat auto-generated function names as original symbols.

A future command shape (template only; **not executed**):

```text
analyzeHeadless.bat <non-synced-analysis-directory> ReconProbe -import <absolute-path-to-identified-image> -noanalysis -readOnly -max-cpu 2 -log <non-synced-log-path>
```

Before doing so, choose and validate a non-synced analysis location outside the game tree, and update the workspace-only output rule in AGENTS.md for that explicit directory. Do not place program databases in this OneDrive workspace: they can contain original binary bytes even when no executable copy is visible. No such project was created in this assignment. A persistent analysis run will need a separate deliberate configuration; the template is only an import probe.
