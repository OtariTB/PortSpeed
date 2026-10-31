"""Compare two inventory snapshots, including names, SHA-256, sizes and mtimes."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('before',type=Path);p.add_argument('after',type=Path)
    args=p.parse_args()
    before=json.loads(args.before.read_text());after=json.loads(args.after.read_text())
    a={r['path']:r for r in before['files']};b={r['path']:r for r in after['files']}
    changed=[name for name in a.keys()&b.keys() if any(a[name].get(k)!=b[name].get(k) for k in ('sha256','size','mtime_ns'))]
    clean=not (before['errors'] or after['errors'] or before['skipped_reparse_or_special'] or after['skipped_reparse_or_special'])
    hashed=all('sha256' in r for r in [*a.values(),*b.values()])
    stable=all(r['stable_metadata_during_read'] for r in [*a.values(),*b.values()])
    report={'files_before':len(a),'files_after':len(b),'added':sorted(b.keys()-a.keys()),'removed':sorted(a.keys()-b.keys()),
            'changed_hash_size_or_mtime':sorted(changed),'all_hashed':hashed,'clean_scans':clean,'stable_during_reads':stable}
    print(json.dumps(report,indent=2))
    if not clean or not hashed or not stable or a.keys()!=b.keys() or changed:raise SystemExit(1)


if __name__=='__main__':main()
