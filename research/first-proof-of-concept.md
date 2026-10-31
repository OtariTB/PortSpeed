# Recommended first native-browser proof of concept

Historical proposal from Phase 1. [Phase 2](phase2-status.md) implemented the texture-viewer milestone using a verified uncompressed container from `GLOBAL/LOADINGTEXTURES.BUN`. The initial car-pack candidate needs CIP/JDLZ decoding and remains unsupported. The decoder is authored AssemblyScript compiled to WASM, not a C++ engine reconstruction.

Build a **single-texture viewer driven by a reconstructed asset reader compiled to WebAssembly**, after validating that reader's format. This is a small, relevant slice of the original engine's asset-loading path. It is not yet an engine port or evidence of gameplay compatibility.

Candidate input: `CARS/240SX/TEXTURES.BIN` (421,248 bytes). Its path and repeated prefix make it worth investigating, but no texture records or compression details have been decoded. If it proves too complex, select another small, nonempty texture candidate based on evidence, not extension alone.

1. Establish the executable baseline. Trace the game's reader or obtain a primary format implementation with applicable licensing; document each supported field, offset, size, alignment, byte order and compression behavior. Confirm across multiple files. Stop at unknown structures.
2. Specify a narrow C/C++ reader API: input byte span and validated texture selection; output dimensions, pixel format and decoded pixels or an explicit unsupported/error result. Bound every offset and allocation. Use synthetic, redistributable fixtures for malformed lengths and valid minimal cases.
3. Verify or install a WASM toolchain in a later implementation phase. Build the same reader natively and to WASM. Compare output metadata and pixel hashes on local samples; no original binary bytes are checked in.
4. Let the user select their local file in a browser. Process it entirely locally through the WASM reader. Upload decoded pixels as one texture and draw a quad, initially with a single WebGL2 rendering path. Capability-check the browser; WebGPU is a later renderer option. Renderer choice is a scope recommendation, not a measured capability of this machine.
5. Acceptance: native and WASM outputs agree, unsupported/malformed files fail safely, the selected texture displays with verified dimensions/orientation/channels, and the shipped app contains only authored code and synthetic fixtures. Original files never leave the user's machine. Record the tested browser, compiler version and file hash locally.

An early intermediate milestone can list validated container records without rendering, but merely displaying a file header does not satisfy the texture-viewer milestone. Do not start with a full car, track, race, audio decoder, vehicle physics or Direct3D translation layer. Geometry, material bindings, streaming and gameplay should follow only after the asset pipeline has evidence-backed tests.

Schedule cannot be estimated credibly until the first format and executable baseline are understood. The immediate next research task is the reader specification, not coding speculative parsers. This reconnaissance has implemented neither gameplay nor the proposed viewer.
