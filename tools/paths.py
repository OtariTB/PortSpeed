"""Shared path checks for read-only source access and local research outputs."""
from pathlib import Path
from recon import reparse


def safe_path(path):
    path=Path(path).absolute()
    for p in (path,*path.parents):
        if p.exists() and reparse(p):
            raise ValueError('reparse path refused: '+str(p))
    return path.resolve()
