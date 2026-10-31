"""Read-only inventory/header/PE inspector; standard library only."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import mmap
import os
from pathlib import Path
import stat

from pe_headers import inspect_pe

WORKSPACE = Path(__file__).resolve().parents[1]


def reparse(path):
    s = path.lstat()
    return path.is_symlink() or bool(getattr(s, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def validate_paths(source, output):
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if not source.is_dir():
        raise ValueError('source must be a directory')
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('source and output must not overlap')
    if not output.is_relative_to(WORKSPACE / 'research' / 'local'):
        raise ValueError('output must be under workspace/research/local')
    if source.is_relative_to(WORKSPACE) or WORKSPACE.is_relative_to(source):
        raise ValueError('source and workspace must not overlap')
    for base in (source, output):
        for p in (base, *base.parents):
            if p.exists() and reparse(p):
                raise ValueError('reparse point in path: ' + str(p))
    return source, output


def inventory(root, hash_all=False):
    rows, errors, skipped = [], [], []
    def onerror(exc):
        errors.append(str(exc))
    for folder, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        for name in list(dirs):
            p = Path(folder) / name
            if reparse(p):
                skipped.append(str(p.relative_to(root)))
                dirs.remove(name)
        for name in sorted(files):
            p = Path(folder) / name
            rel = p.relative_to(root).as_posix()
            try:
                if reparse(p) or not p.is_file():
                    skipped.append(rel)
                    continue
                before = p.stat()
                row = dict(path=rel, size=before.st_size, mtime_ns=before.st_mtime_ns,
                           extension=p.suffix.lower() or '(none)')
                with p.open('rb') as f:
                    header = f.read(32)
                    row['header_hex'] = header.hex(' ')
                    row['header_ascii'] = ''.join(chr(b) if 32 <= b < 127 else '.' for b in header)
                    if hash_all or header[:2] == b'MZ':
                        f.seek(0)
                        digest = hashlib.sha256()
                        for block in iter(lambda: f.read(1024 * 1024), b''):
                            digest.update(block)
                        row['sha256'] = digest.hexdigest()
                    if header[:2] == b'MZ':
                        try:
                            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
                                row['pe'] = inspect_pe(data)
                        except (ValueError, OSError) as exc:
                            row['pe_error'] = str(exc)
                after = p.stat()
                row['stable_metadata_during_read'] = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
                rows.append(row)
            except OSError as exc:
                errors.append(rel + ': ' + str(exc))
    return dict(files=sorted(rows, key=lambda r: r['path']), errors=errors, skipped_reparse_or_special=skipped)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=WORKSPACE / 'config/local.json')
    parser.add_argument('--output', type=Path, default=WORKSPACE / 'research/local/inventory')
    parser.add_argument('--hash-all', action='store_true', help='stream SHA-256 for every file (can take time)')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    root, output = validate_paths(config['game_root'], args.output)
    if output.exists():
        raise ValueError('output already exists; select a fresh run directory')
    report = inventory(root, args.hash_all)
    report.update(source=str(root), generated_utc=datetime.now(timezone.utc).isoformat(), hash_all=args.hash_all)
    # Revalidate after scanning, before writing. Not a sandbox against concurrent path substitution.
    validate_paths(root, output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    counts = Counter(r['extension'] for r in report['files'])
    sizes = Counter()
    for r in report['files']:
        sizes[r['extension']] += r['size']
    lines = ['# Local inventory', '', f"Files: {len(report['files'])}; bytes: {sum(sizes.values())}",
             f"Read errors: {len(report['errors'])}; skipped: {len(report['skipped_reparse_or_special'])}",
             '', '| Extension (not format proof) | Count | Bytes |', '|---|---:|---:|']
    lines += [f'| {e} | {n} | {sizes[e]} |' for e, n in counts.most_common()]
    lines += ['', '## Largest files', '']
    lines += [f"- `{r['path']}`: {r['size']} bytes" for r in sorted(report['files'], key=lambda r: -r['size'])[:30]]
    lines += ['', '## Static PE DLL names', '', 'Imports do not establish runtime loading, transitive dependencies, or browser portability.', '']
    for r in report['files']:
        if 'pe' in r:
            lines += [f"- `{r['path']}` ({r['pe']['bits']}-bit, {r['pe']['machine']}): " + ', '.join(r['pe']['imports']),
                      '  - Delay imports: ' + ', '.join(r['pe']['delay_imports']),
                      '  - Warnings: ' + '; '.join(r['pe']['warnings'])]
    lines += ['', '## Errors / skipped', '', *report['errors'], *report['skipped_reparse_or_special']]
    (output / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"Report: {output}; files={len(report['files'])}; errors={len(report['errors'])}")


if __name__ == '__main__':
    main()
