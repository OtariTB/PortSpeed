/**
 * Need for Speed ProStreet - Background I/O Worker & Asset Streamer.
 *
 * Runs off the main UI/game thread. Manages Origin Private File System (OPFS) sparse caching,
 * on-demand 1 MiB chunk streaming via HTTP Range requests, and asset preloading.
 */

import {
  OPFS_BLOCK_SIZE,
  OPFS_CACHE_DIR,
  OPFS_DATA_BASE_URL,
  ManifestFileEntry,
  GameManifest,
  getCacheKey,
  calculateBlockCount,
  calculateBlockRange,
  getAssetUrl,
  fetchByteRange,
  MemoryBlockCache,
} from './io_datacache.js';

export interface FileDescriptor {
  fd: number;
  entry: ManifestFileEntry;
  cacheKey: string;
  blockCount: number;
  syncHandle: any | null;
  haveMap: Uint8Array;
}

export interface PreloadProgress {
  file: string;
  bytesLoaded: number;
  bytesTotal: number;
  blocksLoaded: number;
  blocksTotal: number;
  percent: number;
}

export class AssetIOEngine {
  private manifest: Map<string, ManifestFileEntry> = new Map();
  private openFiles: Map<number, FileDescriptor> = new Map();
  private nextFd: number = 10;
  private cacheDir: any | null = null;
  private memFallback: MemoryBlockCache = new MemoryBlockCache();
  private dataBaseUrl: string;

  constructor(dataBaseUrl: string = OPFS_DATA_BASE_URL) {
    this.dataBaseUrl = dataBaseUrl;
  }

  /**
   * Initializes OPFS cache directory handle if available in this environment.
   */
  public async initOPFS(): Promise<boolean> {
    if (typeof navigator !== 'undefined' && 'storage' in navigator && navigator.storage.getDirectory) {
      try {
        const root = await navigator.storage.getDirectory();
        this.cacheDir = await root.getDirectoryHandle(OPFS_CACHE_DIR, { create: true });
        return true;
      } catch (e) {
        console.warn('[IO] OPFS unavailable, using memory fallback:', e);
      }
    }
    return false;
  }

  /**
   * Loads and indexes the game asset manifest.
   */
  public setManifest(manifest: GameManifest): void {
    this.manifest.clear();
    for (const file of manifest.files) {
      const normalized = this.normalizePath(file.path);
      this.manifest.set(normalized, file);
    }
  }

  public normalizePath(path: string): string {
    return path.replace(/\\/g, '/').replace(/^\/+/, '').toLowerCase();
  }

  public getManifestEntry(path: string): ManifestFileEntry | null {
    return this.manifest.get(this.normalizePath(path)) ?? null;
  }

  /**
   * Opens an asset file by path and prepares its chunk tracking state.
   */
  public async open(path: string): Promise<FileDescriptor> {
    const entry = this.getManifestEntry(path);
    if (!entry) {
      throw new Error(`[IO] File not found in manifest: ${path}`);
    }

    const cacheKey = getCacheKey(entry);
    const blockCount = calculateBlockCount(entry.size);
    const haveMap = new Uint8Array(blockCount);
    let syncHandle = null;

    if (this.cacheDir) {
      try {
        const fileHandle = await this.cacheDir.getFileHandle(cacheKey, { create: true });
        const mapHandle = await this.cacheDir.getFileHandle(`${cacheKey}.have`, { create: true });

        if ('createSyncAccessHandle' in fileHandle) {
          syncHandle = await fileHandle.createSyncAccessHandle({ mode: 'readwrite-unsafe' });
        }
        if ('createSyncAccessHandle' in mapHandle) {
          const mapSync = await mapHandle.createSyncAccessHandle({ mode: 'readwrite-unsafe' });
          if (mapSync.getSize() === blockCount) {
            mapSync.read(haveMap, { at: 0 });
          } else {
            mapSync.truncate(0);
            mapSync.write(haveMap, { at: 0 });
          }
          mapSync.close();
        }
      } catch (e) {
        console.warn(`[IO] OPFS open error for ${entry.path}:`, e);
      }
    }

    const fd = this.nextFd++;
    const desc: FileDescriptor = {
      fd,
      entry,
      cacheKey,
      blockCount,
      syncHandle,
      haveMap,
    };
    this.openFiles.set(fd, desc);
    return desc;
  }

  /**
   * Reads a byte slice from an open file, pulling any missing 1 MiB blocks over HTTP on demand.
   */
  public async read(fd: number, offset: number, length: number): Promise<Uint8Array> {
    const desc = this.openFiles.get(fd);
    if (!desc) {
      throw new Error(`[IO] Invalid file descriptor: ${fd}`);
    }

    if (offset >= desc.entry.size || length <= 0) {
      return new Uint8Array(0);
    }

    const readLen = Math.min(length, desc.entry.size - offset);
    const outBuffer = new Uint8Array(readLen);

    const firstBlock = Math.floor(offset / OPFS_BLOCK_SIZE);
    const lastBlock = Math.floor((offset + readLen - 1) / OPFS_BLOCK_SIZE);

    for (let bi = firstBlock; bi <= lastBlock; ++bi) {
      const block = await this.ensureBlock(desc, bi);
      const bRange = calculateBlockRange(desc.entry.size, bi);

      // Overlap calculation between [offset, offset + readLen) and [bRange.start, bRange.end)
      const sliceStartInFile = Math.max(offset, bRange.start);
      const sliceEndInFile = Math.min(offset + readLen, bRange.end);
      const sliceLen = sliceEndInFile - sliceStartInFile;

      const blockOffset = sliceStartInFile - bRange.start;
      const outOffset = sliceStartInFile - offset;

      outBuffer.set(block.subarray(blockOffset, blockOffset + sliceLen), outOffset);
    }

    return outBuffer;
  }

  /**
   * Ensures that a specific 1 MiB chunk is cached locally (in OPFS or memory fallback).
   */
  public async ensureBlock(desc: FileDescriptor, blockIndex: number): Promise<Uint8Array> {
    const bRange = calculateBlockRange(desc.entry.size, blockIndex);

    // 1. Check if already cached in OPFS
    if (desc.syncHandle && desc.haveMap[blockIndex] === 1) {
      const blockBuffer = new Uint8Array(bRange.length);
      desc.syncHandle.read(blockBuffer, { at: bRange.start });
      return blockBuffer;
    }

    // 2. Check memory fallback
    if (this.memFallback.hasBlock(desc.cacheKey, blockIndex)) {
      const memBlock = this.memFallback.getBlock(desc.cacheKey, blockIndex);
      if (memBlock) return memBlock;
    }

    // 3. Fetch missing block via HTTP Range Request
    const url = getAssetUrl(this.dataBaseUrl, desc.entry.path);
    const downloaded = await fetchByteRange(url, bRange.start, bRange.end);

    // 4. Save into OPFS if handle is available
    if (desc.syncHandle) {
      try {
        desc.syncHandle.write(downloaded, { at: bRange.start });
        desc.haveMap[blockIndex] = 1;
        if (this.cacheDir) {
          const mapHandle = await this.cacheDir.getFileHandle(`${desc.cacheKey}.have`, { create: false });
          if ('createSyncAccessHandle' in mapHandle) {
            const mapSync = await mapHandle.createSyncAccessHandle({ mode: 'readwrite-unsafe' });
            mapSync.write(new Uint8Array([1]), { at: blockIndex });
            mapSync.close();
          }
        }
      } catch (e) {
        console.warn(`[IO] Failed to persist block ${blockIndex} to OPFS:`, e);
      }
    }

    // 5. Save into memory fallback
    this.memFallback.putBlock(desc.cacheKey, blockIndex, downloaded);
    return downloaded;
  }

  /**
   * Preloads full files into OPFS/cache ahead of time with progress callbacks.
   */
  public async preloadFiles(
    paths: string[],
    onProgress?: (p: PreloadProgress) => void
  ): Promise<void> {
    let totalBytes = 0;
    const entries: ManifestFileEntry[] = [];

    for (const p of paths) {
      const e = this.getManifestEntry(p);
      if (e) {
        entries.push(e);
        totalBytes += e.size;
      }
    }

    let loadedBytes = 0;
    let totalBlocks = 0;
    for (const e of entries) totalBlocks += calculateBlockCount(e.size);
    let loadedBlocks = 0;

    for (const entry of entries) {
      const desc = await this.open(entry.path);
      for (let bi = 0; bi < desc.blockCount; ++bi) {
        const bRange = calculateBlockRange(entry.size, bi);
        await this.ensureBlock(desc, bi);
        loadedBytes += bRange.length;
        loadedBlocks++;

        if (onProgress) {
          onProgress({
            file: entry.path,
            bytesLoaded: loadedBytes,
            bytesTotal: totalBytes,
            blocksLoaded: loadedBlocks,
            blocksTotal: totalBlocks,
            percent: totalBytes > 0 ? (loadedBytes / totalBytes) * 100 : 100,
          });
        }
      }
      this.close(desc.fd);
    }
  }

  public close(fd: number): void {
    const desc = this.openFiles.get(fd);
    if (desc) {
      if (desc.syncHandle) {
        try { desc.syncHandle.close(); } catch (_) {}
      }
      this.openFiles.delete(fd);
    }
  }
}

