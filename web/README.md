# Local ProStreet texture viewer

```powershell
# In web/
npm ci --ignore-scripts
npm run dev
# Separate checks:
npm test
npm run build
```

Select your own `GLOBAL/LOADINGTEXTURES.BUN`. Also validated: `GLOBAL/UniqueBootTextures.bin` and `GLOBAL/NISOverlayTextures.bin`. Standalone version-8 TPK only; DXT5 pixels only. Unsupported files show a diagnostic, never substitute content.

`src/tpk.ts` validates container metadata. `assembly/bc3.ts` compiles to actual WebAssembly and decodes BC3 blocks into RGBA. `src/decoder.ts` handles the memory ABI. `src/renderer.ts` owns WebGL2 resources and displays the base mip with nearest filtering and transparency over a CSS checkerboard. There is no server asset endpoint, dependency on game executables, or game asset in `public/` or `dist/`.

`npm run test:browser` uses an already-installed Google Chrome, starts its own loopback Vite server, reads the machine-local game path and Python validation report, and checks original texture hashes against WebGL framebuffer readback. First run the Python validator as described in [the Phase 2 guide](../research/phase2-status.md). The test forces software SwiftShader and stops its browser/server on exit. A hardware GPU performance claim is not implied.

Rendering and container/decoder modules are separate so a future mesh/material pipeline can reuse them. No scene graph, mesh decoder, vehicle controls, physics, or gameplay placeholders are presented as implemented features.
