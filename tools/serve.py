#!/usr/bin/env python3
"""
Need for Speed ProStreet - Local Web & Asset Streaming Server.

Serves the web client bundle from web/ (or web/dist/) and mounts the authentic
game asset directory under /data/ with full HTTP Range Request support (206 Partial Content),
CORS, and Cross-Origin-Opener-Policy / Cross-Origin-Embedder-Policy isolation headers.
"""

import argparse
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
import mimetypes
import os
from pathlib import Path
import sys

DEFAULT_GAME_DIR = Path(r"C:\Games\Pro Street\Need For Spped - Pro Street")
DEFAULT_WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class ProStreetHTTPHandler(SimpleHTTPRequestHandler):
    game_dir: Path = DEFAULT_GAME_DIR
    web_dir: Path = DEFAULT_WEB_DIR

    def end_headers(self):
        # Enable SharedArrayBuffer and multi-threaded WebAssembly
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        # Handle /data/<rel_path> asset route
        if self.path.startswith("/data/"):
            self.serve_game_asset()
            return

        super().do_GET()

    def serve_game_asset(self):
        raw_rel = self.path[len("/data/"):].split("?")[0]
        # Prevent traversal
        clean_rel = os.path.normpath(raw_rel).lstrip("/\\")
        if clean_rel.startswith(".."):
            self.send_error(HTTPStatus.FORBIDDEN, "Path traversal forbidden")
            return

        target_file = self.game_dir / clean_rel
        if not target_file.is_file():
            fallback = self.game_dir / "Need For Spped - Pro Street" / clean_rel
            if fallback.is_file():
                target_file = fallback
            else:
                self.send_error(HTTPStatus.NOT_FOUND, f"Game asset not found: {clean_rel}")
                return

        file_size = target_file.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(target_file))
        if not mime_type:
            mime_type = "application/octet-stream"

        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            try:
                parts = range_header[6:].split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else file_size - 1
                if start >= file_size or end < start:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return

                end = min(end, file_size - 1)
                chunk_len = end - start + 1

                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(chunk_len))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(target_file, "rb") as f:
                    f.seek(start)
                    remaining = chunk_len
                    while remaining > 0:
                        buf = f.read(min(remaining, 65536))
                        if not buf:
                            break
                        self.wfile.write(buf)
                        remaining -= len(buf)
                return
            except Exception as e:
                print(f"Error serving range for {clean_rel}: {e}", file=sys.stderr)
                return

        # Normal full GET
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

        with open(target_file, "rb") as f:
            while True:
                buf = f.read(65536)
                if not buf:
                    break
                self.wfile.write(buf)


def run_server(port: int, host: str, game_dir: Path, web_dir: Path):
    ProStreetHTTPHandler.game_dir = game_dir
    ProStreetHTTPHandler.web_dir = web_dir

    # Change cwd to web directory for standard file serving
    serve_root = web_dir / "dist" if (web_dir / "dist" / "index.html").is_file() else web_dir
    os.chdir(serve_root)

    server = HTTPServer((host, port), ProStreetHTTPHandler)
    print("=====================================================================")
    print(" PortSpeed Local Game & Asset Server (Step 7.2)")
    print("=====================================================================")
    print(f" Web root:       {serve_root}")
    print(f" Game directory: {game_dir} (mounted at /data/)")
    print(f" Listening on:   http://{host}:{port}/")
    print(" Press Ctrl+C to stop.")
    print("=====================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=Path(os.environ.get("PROSTREET_GAME_DIR", DEFAULT_GAME_DIR)),
        help="Path to game files directory",
    )
    parser.add_argument(
        "--web-dir",
        type=Path,
        default=DEFAULT_WEB_DIR,
        help="Path to web directory",
    )
    args = parser.parse_args()
    run_server(args.port, args.host, args.game_dir, args.web_dir)


if __name__ == "__main__":
    main()

