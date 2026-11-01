import { defineConfig } from 'vite';
import fs from 'fs';
import path from 'path';

const GAME_DIR = process.env.PROSTREET_GAME_DIR || 'C:\\Games\\Pro Street\\Need For Spped - Pro Street';

/**
 * Custom Vite plugin providing HTTP Range Request (206 Partial Content) support
 * and local game folder streaming for OPFS chunk manager.
 */
function gameDataServerPlugin() {
  const mountRoute = (req: any, res: any, next: any) => {
    const url = req.url || '';
    if (!url.startsWith('/data/')) {
      return next();
    }

    const relPath = decodeURIComponent(url.slice('/data/'.length).split('?')[0]);
    // Prevent directory traversal
    const safeRel = path.normalize(relPath).replace(/^(\.\.[\/\\])+/, '');
    let absPath = path.join(GAME_DIR, safeRel);

    if (!fs.existsSync(absPath) || !fs.statSync(absPath).isFile()) {
      const fallback = path.join(GAME_DIR, 'Need For Spped - Pro Street', safeRel);
      if (fs.existsSync(fallback) && fs.statSync(fallback).isFile()) {
        absPath = fallback;
      } else {
        res.statusCode = 404;
        res.end(`[Vite /data/] Asset not found: ${relPath}`);
        return;
      }
    }

    const stat = fs.statSync(absPath);
    const fileSize = stat.size;
    const rangeHeader = req.headers.range;

    // Standard headers
    res.setHeader('Accept-Ranges', 'bytes');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cross-Origin-Resource-Policy', 'cross-origin');
    res.setHeader('Content-Type', 'application/octet-stream');

    if (rangeHeader) {
      // Range: bytes=start-end
      const parts = rangeHeader.replace(/bytes=/, '').split('-');
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;

      if (isNaN(start) || start >= fileSize || (parts[1] && end < start)) {
        res.statusCode = 416; // Range Not Satisfiable
        res.setHeader('Content-Range', `bytes */${fileSize}`);
        res.end();
        return;
      }

      const clampedEnd = Math.min(end, fileSize - 1);
      const chunkSize = clampedEnd - start + 1;

      res.statusCode = 206; // Partial Content
      res.setHeader('Content-Range', `bytes ${start}-${clampedEnd}/${fileSize}`);
      res.setHeader('Content-Length', chunkSize);

      const stream = fs.createReadStream(absPath, { start, end: clampedEnd });
      stream.pipe(res);
    } else {
      res.statusCode = 200;
      res.setHeader('Content-Length', fileSize);
      const stream = fs.createReadStream(absPath);
      stream.pipe(res);
    }
  };

  return {
    name: 'game-data-server-plugin',
    configureServer(server: any) {
      server.middlewares.use(mountRoute);
    },
    configurePreviewServer(server: any) {
      server.middlewares.use(mountRoute);
    },
  };
}

export default defineConfig({
  server: {
    host: '127.0.0.1',
    port: 5173,
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp',
    },
  },
  plugins: [gameDataServerPlugin()],
});

