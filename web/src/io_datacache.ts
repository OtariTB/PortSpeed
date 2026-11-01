/**
 * Need for Speed ProStreet - OPFS Game Data Cache & Chunk Manager.
 *
 * Implements chunk-based (1 MiB block) sparse caching on the Origin Private File System (OPFS)
 * backed by HTTP Range requests for streaming the 5.6 GB game assets seamlessly.
 */

// WebWorker / OPFS Sync Access Handle declaration for environments with standard DOM lib
type FileSystemSyncAccessHandle = any;

export const OPFS_BLOCK_SIZE = 1048576; // 1 MiB (1 << 20)
export const OPFS_CACHE_DIR = 'prostreet-cache';
export const OPFS_DATA_BASE_URL = '/data/';
export const OPFS_MANIFEST_URL = '/data-manifest.json';

export interface ManifestFileEntry {
  path: string;
  size: number;
  mtime?: number;
  isDir?: boolean;
}

export interface GameManifest {
  files: ManifestFileEntry[];
  totalBytes: number;
}

export interface CachedFileRecord {
  handle: FileSystemSyncAccessHandle | null;
  haveMap: Uint8Array;
  haveHandle: FileSystemSyncAccessHandle | null;
  fileEntry: ManifestFileEntry;
}

/**
 * Generates a filesystem-safe unique cache key for an asset file based on path and size.
 */
export function getCacheKey(entry: ManifestFileEntry): string {
  const safePath = entry.path.replace(/[^A-Za-z0-9._-]/g, '_');
  const mtime = entry.mtime ?? 0;
  return `${safePath}.${entry.size}.${mtime}`;
}

export function calculateBlockCount(fileSize: number): number {
  if (fileSize <= 0) return 0;
  return Math.ceil(fileSize / OPFS_BLOCK_SIZE);
}

export function calculateBlockRange(
  fileSize: number,
  blockIndex: number
): { start: number; end: number; length: number } {
  const start = blockIndex * OPFS_BLOCK_SIZE;
  const end = Math.min(start + OPFS_BLOCK_SIZE, fileSize);
  return { start, end, length: end - start };
}

/**
 * Builds HTTP range request URL for an asset path.
 */
export function getAssetUrl(base: string, relativePath: string): string {
  const cleanBase = base.endsWith('/') ? base : base + '/';
  const cleanPath = relativePath.replace(/^[\/\\]+/, '').replace(/\\/g, '/');
  return cleanBase + cleanPath.split('/').map(encodeURIComponent).join('/');
}

/**
 * Fetches a specific byte range over HTTP using standard Range headers.
 */
export async function fetchByteRange(
  url: string,
  start: number,
  endExclusive: number
): Promise<Uint8Array> {
  const rangeHeader = `bytes=${start}-${endExclusive - 1}`;
  const response = await fetch(url, {
    headers: { Range: rangeHeader },
  });

  if (response.status === 206 || response.status === 200) {
    const arrayBuffer = await response.arrayBuffer();
    return new Uint8Array(arrayBuffer);
  }

  throw new Error(`HTTP Range fetch failed (${response.status}): ${url} [${rangeHeader}]`);
}

/**
 * In-memory fallback block cache for environments without OPFS (e.g. Node.js unit tests or memory-only mode).
 */
export class MemoryBlockCache {
  private blocks = new Map<string, Uint8Array>();
  private haveMaps = new Map<string, Uint8Array>();

  public getBlock(key: string, blockIndex: number): Uint8Array | null {
    const blockKey = `${key}:${blockIndex}`;
    return this.blocks.get(blockKey) ?? null;
  }

  public putBlock(key: string, blockIndex: number, blockData: Uint8Array): void {
    const blockKey = `${key}:${blockIndex}`;
    this.blocks.set(blockKey, blockData);

    let map = this.haveMaps.get(key);
    if (!map) {
      map = new Uint8Array(blockIndex + 1);
      this.haveMaps.set(key, map);
    } else if (map.length <= blockIndex) {
      const newMap = new Uint8Array(blockIndex + 1);
      newMap.set(map);
      map = newMap;
      this.haveMaps.set(key, map);
    }
    map[blockIndex] = 1;
  }

  public hasBlock(key: string, blockIndex: number): boolean {
    const map = this.haveMaps.get(key);
    return !!(map && map[blockIndex] === 1);
  }

  public getHaveMap(key: string): Uint8Array | null {
    return this.haveMaps.get(key) ?? null;
  }
}

