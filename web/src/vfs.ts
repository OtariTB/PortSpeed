/**
 * Need for Speed ProStreet - Virtual File System (VFS) Linear Memory Bridge.
 *
 * Interfaces between the browser's AssetIOEngine / OPFS chunk streamer
 * and the 1:1 guest WebAssembly linear memory, supplying data to Win32 ReadFile and CRT fread.
 */

import { AssetIOEngine, FileDescriptor } from './io_worker.js';

export interface VfsFileHandle {
  handleId: number;
  engineFd: number;
  filePath: string;
  size: number;
  filePointer: number;
}

export class VirtualFileSystem {
  private ioEngine: AssetIOEngine;
  private handles: Map<number, VfsFileHandle> = new Map();
  private nextHandleId: number = 0x100;

  constructor(ioEngine: AssetIOEngine) {
    this.ioEngine = ioEngine;
  }

  /**
   * Opens a file via the IO engine and returns a virtual handle.
   */
  public async openFile(path: string): Promise<number> {
    const desc = await this.ioEngine.open(path);
    const handleId = this.nextHandleId++;
    this.handles.set(handleId, {
      handleId,
      engineFd: desc.fd,
      filePath: path,
      size: desc.entry.size,
      filePointer: 0,
    });
    return handleId;
  }

  /**
   * Reads data from file directly into guest WebAssembly memory.
   */
  public async readBytesToGuest(
    handleId: number,
    guestBuffer: ArrayBufferLike,
    targetGuestVA: number,
    bytesToRead: number
  ): Promise<number> {
    const handle = this.handles.get(handleId);
    if (!handle) {
      throw new Error(`[VFS] Invalid file handle: ${handleId}`);
    }

    if (handle.filePointer >= handle.size || bytesToRead <= 0) {
      return 0;
    }

    const actualToRead = Math.min(bytesToRead, handle.size - handle.filePointer);
    const chunk = await this.ioEngine.read(handle.engineFd, handle.filePointer, actualToRead);

    const dest = new Uint8Array(guestBuffer, targetGuestVA, chunk.length);
    dest.set(chunk);

    handle.filePointer += chunk.length;
    return chunk.length;
  }

  /**
   * Sets current file pointer (emulating Win32 SetFilePointer and CRT fseek).
   */
  public setPointer(handleId: number, offset: number, origin: 'begin' | 'current' | 'end'): number {
    const handle = this.handles.get(handleId);
    if (!handle) {
      throw new Error(`[VFS] Invalid file handle: ${handleId}`);
    }

    let newPtr = handle.filePointer;
    if (origin === 'begin') newPtr = offset;
    else if (origin === 'current') newPtr += offset;
    else if (origin === 'end') newPtr = handle.size + offset;

    handle.filePointer = Math.max(0, Math.min(newPtr, handle.size));
    return handle.filePointer;
  }

  public getPointer(handleId: number): number {
    const handle = this.handles.get(handleId);
    return handle ? handle.filePointer : 0;
  }

  public getFileSize(handleId: number): number {
    const handle = this.handles.get(handleId);
    return handle ? handle.size : 0;
  }

  public closeFile(handleId: number): void {
    const handle = this.handles.get(handleId);
    if (handle) {
      this.ioEngine.close(handle.engineFd);
      this.handles.delete(handleId);
    }
  }
}

