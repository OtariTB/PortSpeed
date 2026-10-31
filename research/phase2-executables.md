# Executable identification — Phase 2

Checked on 2026-10-30. Exact paths and full PE section/import metadata are in ignored `local/phase2/executables.json`; raw-section hashes are in `executable-sections.json`. `tools/identify_executables.ps1` reads version resources and rehashes every candidate without loading executable code. It reuses PE metadata only when the current hash matches the Phase 1 snapshot.

The user explicitly confirmed launching `Need For Spped - Pro Street/nfs.exe`. This establishes the working installation's launch target by user report, not by observing a running process. The file's position alongside the assets and DLLs independently makes it the likely default launch target. No unknown binaries were executed. A read-only `Get-Process nfs` check returned no process at the time of inspection.

Paths below are relative to `Need For Spped - Pro Street`.

| File | Bytes | PE / image base | Entry RVA | COFF timestamp (raw, untrusted) | Sections |
|---|---:|---|---|---:|---:|
| `nfs.exe` | 28,739,656 | PE32 x86 / `0x400000` | `0x428c25` | 1197239854 | 10 |
| `nfs.exe.org` | 13,120,776 | PE32 x86 / `0x400000` | `0x12bda10` | 1200350722 | 10 |
| `Crack.1.1-ViTALiTY/nfs.exe` | 3,765,248 | PE32 x86 / `0x400000` | `0x16aa080` | 1445659290 | 3 |

SHA-256:

```text
nfs.exe
ee8a71c7c1e42923deb728e39a89317645cbcf26fc87cc48d3e07ade4dce2f72
nfs.exe.org
8f515be62a479a4ccc5f0d6b0270be793c5fdeb7f5172d0b77ce182f24afc529
Crack.1.1-ViTALiTY/nfs.exe
2983cd2821d5da3565757ad829292e29dc51fbcadf1c1d1c46c06d4439522af5
```

For **all three**, FileVersionInfo returned blank FileVersion, ProductVersion, FileDescription and OriginalFilename. No signed publisher identity or trusted retail hash has been established. A folder named `1.1`, timestamps, successful launch, and the `.org` suffix do not authenticate patch level or provenance.

The main and `.org` variants share section names `.text`, `.rdata`, `.data`, `.tls`, `.rsrc`, `ars`, `est`, `artem`, `celare`, `.securom`. However, their `.text` raw data hashes differ despite the same 5,660,672-byte raw section size:

- Main: `c7c35f0fe408bc631c28f42a98af32b865dc73516186a221a57672aaead51dd0`.
- `.org`: `999ab489d31e0c103d9074b0469544ae0ef5ec5993bc4ff1d0a18b0f1effcf50`.

Their `.rdata` hashes also differ. Main `.data` raw size is 6,053,888 bytes; `.org` is 405,504 bytes. These are distinct images, not simply renamed copies. This does not identify which modifications occurred.

The third image has `.ROT`, `.IN`, `.HEAVEN` sections. `.ROT` declares 20,885,504 virtual bytes and zero raw bytes. This is consistent with a nonstandard loading/packing arrangement, but that explanation remains a hypothesis; nothing was unpacked or run. Do not transplant addresses between these images.

Use the user-confirmed main image's hash to label future local static observations. **A clean retail v1.1 baseline is still unverified.** The Phase 2 asset viewer does not load or depend on any of these executables.
