"""Container health probe: find a RUNNING sky_render_worker.py Python process.

No HTTP endpoint exists for render worker. This probe does not require network,
credentials, database permissions or disclosure of process arguments.
"""
from __future__ import annotations
import os
from pathlib import Path


def worker_alive(proc_root: Path = Path('/proc'), exclude_pid: int | None = None) -> bool:
    excluded = os.getpid() if exclude_pid is None else exclude_pid
    for entry in proc_root.iterdir():
        if not entry.name.isdecimal() or int(entry.name) == excluded:
            continue
        try:
            parts = (entry / 'cmdline').read_bytes().split(b'\x00')
            first = Path(os.fsdecode(parts[0])).name.lower() if parts and parts[0] else ''
            if not first.startswith('python'):
                continue
            # Avoid matching shell strings or python -c code containing the name.
            if any(Path(os.fsdecode(x)).name == 'sky_render_worker.py' for x in parts[1:] if x):
                return True
        except (OSError, PermissionError, ValueError):
            continue
    return False


def main() -> int:
    return 0 if worker_alive() else 1


if __name__ == '__main__':
    raise SystemExit(main())
