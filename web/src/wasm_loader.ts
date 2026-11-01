/**
 * Need for Speed ProStreet - WebAssembly Engine Module Loader.
 *
 * Fetches prostreet.json and prostreet.wasm, establishes shared linear memory
 * (1024 MB initial, 4096 MB max, 640 MB guest arena), wires WASI / POSIX
 * syscall shims, and instantiates the recompiled game engine.
 */

export interface ProStreetManifest {
  pages: number;
  maxPages: number;
  guestEnd: number;
  size: number;
  opt: string;
  toolchain: string;
  shards: number;
  functions: number;
  compiledAt: string;
}

export interface ProStreetExports {
  memory: WebAssembly.Memory;
  prostreet_main?: (argc: number, argv: number) => number;
  prostreet_load_pe?: (peVa: number, peSize: number) => number;
  prostreet_get_guest_memory?: () => number;
  prostreet_tick?: () => number;
  [key: string]: any;
}

export interface LoadedEngine {
  instance: WebAssembly.Instance;
  module: WebAssembly.Module;
  memory: WebAssembly.Memory;
  manifest: ProStreetManifest;
  exports: ProStreetExports;
}

export async function fetchManifest(manifestUrl = '/prostreet.json'): Promise<ProStreetManifest> {
  const res = await fetch(manifestUrl);
  if (!res.ok) {
    throw new Error(`Failed to fetch manifest from ${manifestUrl}: HTTP ${res.status}`);
  }
  return await res.json();
}

export function createGuestMemory(manifest: ProStreetManifest): WebAssembly.Memory {
  try {
    return new WebAssembly.Memory({
      initial: manifest.pages,
      maximum: manifest.maxPages,
      shared: true,
    });
  } catch (e) {
    // Fallback to non-shared if SharedArrayBuffer / cross-origin isolation is disabled
    console.warn('[WASM] Shared memory unavailable, falling back to unshared memory:', e);
    return new WebAssembly.Memory({
      initial: Math.min(manifest.pages, 1024),
      maximum: Math.min(manifest.maxPages, 2048),
      shared: false,
    });
  }
}

export function createWasiImports(
  memory: WebAssembly.Memory,
  onStdout?: (text: string) => void
): Record<string, any> {
  return {
    proc_exit: (code: number) => {
      console.log(`[WASM] proc_exit called with code: ${code}`);
    },
    fd_write: (fd: number, iovs: number, iovsLen: number, nwritten: number) => {
      const view = new DataView(memory.buffer);
      const u8 = new Uint8Array(memory.buffer);
      let total = 0;
      let text = '';

      for (let i = 0; i < iovsLen; i++) {
        const ptr = view.getUint32(iovs + i * 8, true);
        const len = view.getUint32(iovs + i * 8 + 4, true);
        const chunk = new TextDecoder('utf-8').decode(u8.subarray(ptr, ptr + len));
        text += chunk;
        total += len;
      }

      view.setUint32(nwritten, total, true);
      if (onStdout) {
        onStdout(text);
      } else if (fd === 1 || fd === 2) {
        console.log(`[NFS-GUEST] ${text.trimEnd()}`);
      }
      return 0; // __WASI_ERRNO_SUCCESS
    },
    fd_read: () => 0,
    fd_seek: () => 0,
    fd_close: () => 0,
    fd_fdstat_get: (_fd: number, statOut: number) => {
      const view = new DataView(memory.buffer);
      view.setUint8(statOut, 2); // character device (stdio)
      view.setUint16(statOut + 2, 0, true);
      return 0;
    },
    fd_fdstat_set_flags: () => 0,
    fd_prestat_get: () => 8, // EBADF (no preopened dirs)
    fd_prestat_dir_name: () => 8,
    args_get: () => 0,
    args_sizes_get: (argc: number, buf_size: number) => {
      const view = new DataView(memory.buffer);
      view.setUint32(argc, 0, true);
      view.setUint32(buf_size, 0, true);
      return 0;
    },
    environ_get: () => 0,
    environ_sizes_get: (count: number, buf_size: number) => {
      const view = new DataView(memory.buffer);
      view.setUint32(count, 0, true);
      view.setUint32(buf_size, 0, true);
      return 0;
    },
    path_open: () => 0,
    path_remove_directory: () => 0,
    path_rename: () => 0,
    path_unlink_file: () => 0,
    clock_time_get: (_id: number, _precision: bigint, timeOut: number) => {
      const nowNs = BigInt(Math.round(performance.now() * 1e6));
      const view = new DataView(memory.buffer);
      view.setBigUint64(timeOut, nowNs, true);
      return 0;
    },
    sched_yield: () => 0,
  };
}

export async function loadProStreetModule(
  wasmUrl = '/prostreet.wasm',
  manifestUrl = '/prostreet.json',
  onStdout?: (text: string) => void
): Promise<LoadedEngine> {
  const manifest = await fetchManifest(manifestUrl);
  const memory = createGuestMemory(manifest);

  const wasi = createWasiImports(memory, onStdout);
  const importObject: WebAssembly.Imports = {
    env: {
      memory,
    },
    wasi_snapshot_preview1: wasi,
  };

  let module: WebAssembly.Module;
  let instance: WebAssembly.Instance;

  if (typeof WebAssembly.instantiateStreaming === 'function') {
    try {
      const res = await WebAssembly.instantiateStreaming(fetch(wasmUrl), importObject);
      module = res.module;
      instance = res.instance;
    } catch (_) {
      const resp = await fetch(wasmUrl);
      const bytes = await resp.arrayBuffer();
      const res = await WebAssembly.instantiate(bytes, importObject);
      module = res.module;
      instance = res.instance;
    }
  } else {
    const resp = await fetch(wasmUrl);
    const bytes = await resp.arrayBuffer();
    const res = await WebAssembly.instantiate(bytes, importObject);
    module = res.module;
    instance = res.instance;
  }

  const exports = instance.exports as ProStreetExports;

  return {
    instance,
    module,
    memory,
    manifest,
    exports,
  };
}

