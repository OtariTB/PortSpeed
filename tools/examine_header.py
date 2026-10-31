"""Print a bounded byte window from a source-relative path; no extraction."""
import argparse
import json
from pathlib import Path
from recon import WORKSPACE, reparse


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('relative_path')
    p.add_argument('--offset', type=lambda s: int(s, 0), default=0)
    p.add_argument('--length', type=int, default=32)
    args = p.parse_args()
    if args.offset < 0 or not 1 <= args.length <= 256:
        p.error('offset must be nonnegative; length must be 1..256')
    config = json.loads((WORKSPACE / 'config/local.json').read_text(encoding='utf-8-sig'))
    root = Path(config['game_root']).resolve(strict=True)
    requested = root / args.relative_path
    for path in (requested, *requested.parents):
        if path.exists() and reparse(path):
            p.error('reparse points are not permitted')
    target = requested.resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        p.error('path must identify a regular file inside the protected source')
    with target.open('rb') as f:
        f.seek(args.offset)
        data = f.read(args.length)
    print(target.relative_to(root).as_posix())
    for i in range(0, len(data), 16):
        b = data[i:i+16]
        print(f'{args.offset+i:08x}  {b.hex(" "):47}  ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in b))
    print(f'{len(data)} bytes read; no field interpretation performed')


if __name__ == '__main__':
    main()
