/**
 * Need for Speed ProStreet - WebAssembly Engine Module Loader.
 *
 * Fetches prostreet.json and prostreet.wasm, wires WASI / POSIX syscall shims,
 * and instantiates the recompiled game engine.
 *
 * Memory contract (single memory): the engine's linear memory is the one the
 * module itself owns. The 1:1 guest address space (PE image, TEB/TLS, D3D9 ring,
 * DirectInput state, audio ring) lives in it, so every host subsystem MUST read
 * and write through `LoadedEngine.memory` and never through a separately created
 * buffer. Modules that instead *import* `env.memory` (legacy/synthetic builds)
 * are still supported: the host-created memory is passed in and the module's
 * exported memory is the same object.
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
  _initialize?: () => void;
  fntab_init?: () => void;
  fntab_count?: () => number;
  prostreet_main?: (argc: number, argv: number) => number;
  prostreet_load_pe?: (peVa: number, peSize: number) => number;
  prostreet_get_guest_memory?: () => number;
  prostreet_tick?: (dtUs?: number) => number;
  [key: string]: any;
}

export interface LoadedEngine {
  instance: WebAssembly.Instance;
  module: WebAssembly.Module;
  memory: WebAssembly.Memory;
  manifest: ProStreetManifest;
  exports: ProStreetExports;
}

/**
 * Tracks WebAssembly instances whose WASI reactor `_initialize()` entry point
 * has already been executed. WASI `crt1-reactor.c` traps with `unreachable` if
 * the raw `_initialize` export is invoked more than once on the same instance.
 */
const initializedReactors = new WeakSet<WebAssembly.Instance>();

/**
 * Tracks WebAssembly instances whose master guest function dispatch table
 * (`g_dtab` via `fntab_init()`) has already been populated.
 */
const initializedDispatchTables = new WeakSet<WebAssembly.Instance>();

/**
 * Runs the module's WASI reactor `_initialize()` entry point at most once per
 * `WebAssembly.Instance`. Returns `true` if `_initialize()` was invoked on this
 * call, or `false` if the instance was already initialized or does not export
 * `_initialize` (e.g. legacy/synthetic builds).
 */
export function initializeReactor(instance: WebAssembly.Instance): boolean {
  if (initializedReactors.has(instance)) {
    return false;
  }
  initializedReactors.add(instance);

  const rawInit = (instance.exports as ProStreetExports)._initialize;
  if (typeof rawInit === 'function') {
    rawInit();
    return true;
  }
  return false;
}

/**
 * Reports whether `initializeReactor` has completed for the given instance.
 */
export function isReactorInitialized(instance: WebAssembly.Instance): boolean {
  return initializedReactors.has(instance);
}

/**
 * Populates the master guest dispatch table (`g_dtab`) by invoking `fntab_init()`
 * at most once per `WebAssembly.Instance`. Must be called after `initializeReactor`.
 * Returns `true` if `fntab_init()` was invoked on this call, or `false` if the
 * instance was already initialized or does not export `fntab_init`.
 */
export function initializeDispatchTable(instance: WebAssembly.Instance): boolean {
  if (initializedDispatchTables.has(instance)) {
    return false;
  }
  initializedDispatchTables.add(instance);

  const rawFntabInit = (instance.exports as ProStreetExports).fntab_init;
  if (typeof rawFntabInit === 'function') {
    rawFntabInit();
    return true;
  }
  return false;
}

/**
 * Reports whether `initializeDispatchTable` has completed for the given instance.
 */
export function isDispatchTableInitialized(instance: WebAssembly.Instance): boolean {
  return initializedDispatchTables.has(instance);
}

/**
 * A linear memory, or a getter returning it. A getter lets WASI shims resolve the
 * module-owned memory lazily, because that memory only exists after instantiation.
 */
export type MemorySource = WebAssembly.Memory | (() => WebAssembly.Memory);

function resolveMemory(source: MemorySource): WebAssembly.Memory {
  return typeof source === 'function' ? source() : source;
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
  memorySource: MemorySource,
  onStdout?: (text: string) => void
): Record<string, any> {
  // Resolved per call: the buffer must be re-read after any memory.grow().
  const mem = (): WebAssembly.Memory => resolveMemory(memorySource);
  return {
    proc_exit: (code: number) => {
      console.log(`[WASM] proc_exit called with code: ${code}`);
    },
    fd_write: (fd: number, iovs: number, iovsLen: number, nwritten: number) => {
      const buffer = mem().buffer;
      const view = new DataView(buffer);
      const u8 = new Uint8Array(buffer);
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
      const view = new DataView(mem().buffer);
      view.setUint8(statOut, 2); // character device (stdio)
      view.setUint16(statOut + 2, 0, true);
      return 0;
    },
    fd_fdstat_set_flags: () => 0,
    fd_prestat_get: () => 8, // EBADF (no preopened dirs)
    fd_prestat_dir_name: () => 8,
    args_get: () => 0,
    args_sizes_get: (argc: number, buf_size: number) => {
      const view = new DataView(mem().buffer);
      view.setUint32(argc, 0, true);
      view.setUint32(buf_size, 0, true);
      return 0;
    },
    environ_get: () => 0,
    environ_sizes_get: (count: number, buf_size: number) => {
      const view = new DataView(mem().buffer);
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
      const view = new DataView(mem().buffer);
      view.setBigUint64(timeOut, nowNs, true);
      return 0;
    },
    sched_yield: () => 0,
  };
}

/**
 * Instantiates a compiled ProStreet module and establishes the single-memory
 * contract. The module's own exported memory is authoritative; a host-created
 * `env.memory` is only supplied (and only used) when the module asks to import one.
 */
export async function instantiateProStreet(
  module: WebAssembly.Module,
  manifest: ProStreetManifest,
  onStdout?: (text: string) => void
): Promise<LoadedEngine> {
  const wantsEnvMemory = WebAssembly.Module.imports(module).some(
    (i) => i.module === 'env' && i.name === 'memory' && i.kind === 'memory'
  );

  const importedMemory: WebAssembly.Memory | null = wantsEnvMemory ? createGuestMemory(manifest) : null;
  let memory: WebAssembly.Memory | null = importedMemory;

  const wasi = createWasiImports(() => {
    if (!memory) {
      throw new Error('[WASM] WASI call before the engine linear memory was resolved');
    }
    return memory;
  }, onStdout);

  const importObject: WebAssembly.Imports = { wasi_snapshot_preview1: wasi };
  if (importedMemory) {
    importObject.env = { memory: importedMemory };
  }

  const instance = await WebAssembly.instantiate(module, importObject);
  const rawExports = instance.exports as ProStreetExports;

  // The module-owned (exported) memory wins; fall back to the imported one.
  if (rawExports.memory instanceof WebAssembly.Memory) {
    memory = rawExports.memory;
  } else if (!importedMemory) {
    throw new Error('[WASM] prostreet module neither exports nor imports a linear memory');
  }

  const engineMemory = memory as WebAssembly.Memory;
  if (engineMemory.buffer.byteLength < manifest.guestEnd) {
    throw new Error(
      `[WASM] engine memory (${engineMemory.buffer.byteLength} bytes) is smaller than the ` +
        `guest arena (${manifest.guestEnd} bytes)`
    );
  }

  // WASI reactor runtime initialization (Task 3.3c-3a) followed immediately by
  // master guest function dispatch table initialization (Task 3.3c-3b).
  initializeReactor(instance);
  initializeDispatchTable(instance);

  const hasInit = typeof rawExports._initialize === 'function';
  const hasFntabInit = typeof rawExports.fntab_init === 'function';
  const exports: ProStreetExports =
    hasInit || hasFntabInit
      ? {
          ...rawExports,
          ...(hasInit
            ? {
                _initialize: () => {
                  initializeReactor(instance);
                },
              }
            : {}),
          ...(hasFntabInit
            ? {
                fntab_init: () => {
                  initializeDispatchTable(instance);
                },
              }
            : {}),
        }
      : rawExports;

  return {
    instance,
    module,
    memory: engineMemory,
    manifest,
    exports,
  };
}

export async function loadProStreetModule(
  wasmUrl = '/prostreet.wasm',
  manifestUrl = '/prostreet.json',
  onStdout?: (text: string) => void
): Promise<LoadedEngine> {
  const manifest = await fetchManifest(manifestUrl);

  let module: WebAssembly.Module;
  if (typeof WebAssembly.compileStreaming === 'function') {
    try {
      module = await WebAssembly.compileStreaming(fetch(wasmUrl));
    } catch (_) {
      // e.g. server does not send application/wasm: fall back to a buffered compile
      const resp = await fetch(wasmUrl);
      module = await WebAssembly.compile(await resp.arrayBuffer());
    }
  } else {
    const resp = await fetch(wasmUrl);
    module = await WebAssembly.compile(await resp.arrayBuffer());
  }

  return instantiateProStreet(module, manifest, onStdout);
}
