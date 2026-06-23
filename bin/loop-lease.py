#!/usr/bin/env python3
"""loop-lease — an atomic single-runner lease for Loobster goal-loops.

The goal-loop must run only ONE instance per worktree (so a ScheduleWakeup/cron
re-entry, or a parallel headless run, backs off instead of colliding). The marker
frontmatter (`runner` / `runnerHeartbeatAt`) is a human-readable mirror, but the
*authoritative* mutex is a lock file claimed atomically here with O_CREAT|O_EXCL —
so two processes racing to acquire cannot both win.

Lock file: `<marker>.lock`, containing `<runner-id>\n<epoch-seconds>`.

Usage:
  loop-lease.py acquire <marker.md> <runner-id> [--ttl N]   # claim or take over a stale lease
  loop-lease.py refresh <marker.md> <runner-id> [--ttl N]   # bump the heartbeat (must hold it)
  loop-lease.py release <marker.md> <runner-id>             # release (must hold it)
  loop-lease.py status  <marker.md>          [--ttl N]      # report holder + freshness

Exit codes:
  0  success (acquired / refreshed / released / status printed)
  3  lease is held by a live (fresh) runner that is not you  -> back off and exit
  2  usage error

Default TTL is 900s (~a few cycles). A lease whose heartbeat is older than TTL is
"stale" and may be taken over.
"""
import os
import sys
import time

DEFAULT_TTL = 900


def _lock_path(marker):
    return marker + ".lock"


def _read_lock(path):
    try:
        with open(path, encoding="utf-8") as f:
            runner = f.readline().strip()
            ts = float(f.readline().strip() or 0)
        return runner, ts
    except (FileNotFoundError, ValueError):
        return None, 0.0


def _write_lock_excl(path, runner):
    """Create the lock atomically. Returns True on success, False if it already exists."""
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"{runner}\n{time.time():.0f}\n")
    return True


def _fresh(ts, ttl):
    return (time.time() - ts) < ttl


def acquire(marker, runner, ttl):
    path = _lock_path(marker)
    if _write_lock_excl(path, runner):
        print(f"acquired {runner}")
        return 0
    holder, ts = _read_lock(path)
    if holder == runner:                       # we already hold it -> refresh
        _force_write(path, runner)
        print(f"acquired {runner} (already held)")
        return 0
    if _fresh(ts, ttl):                         # a live, different runner holds it
        print(f"held by {holder} (age {int(time.time() - ts)}s)")
        return 3
    # Stale lease: take it over. Remove then re-create with O_EXCL so a concurrent
    # takeover race still has exactly one winner.
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    if _write_lock_excl(path, runner):
        print(f"acquired {runner} (took over stale lease from {holder})")
        return 0
    holder, ts = _read_lock(path)              # lost the takeover race
    print(f"held by {holder} (age {int(time.time() - ts)}s)")
    return 3


def _force_write(path, runner):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(f"{runner}\n{time.time():.0f}\n")
    os.replace(tmp, path)


def refresh(marker, runner, ttl):
    path = _lock_path(marker)
    holder, _ = _read_lock(path)
    if holder != runner:
        print(f"not held by {runner} (holder: {holder})")
        return 3
    _force_write(path, runner)
    print(f"refreshed {runner}")
    return 0


def release(marker, runner):
    path = _lock_path(marker)
    holder, _ = _read_lock(path)
    if holder not in (runner, None):
        print(f"not held by {runner} (holder: {holder}) — not releasing")
        return 3
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    print(f"released {runner}")
    return 0


def status(marker, ttl):
    path = _lock_path(marker)
    holder, ts = _read_lock(path)
    if not holder:
        print("free (no live runner)")
        return 0
    age = int(time.time() - ts)
    print(f"{'fresh' if _fresh(ts, ttl) else 'stale'} runner={holder} age={age}s")
    return 0


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 2
    ttl = DEFAULT_TTL
    if "--ttl" in argv:
        i = argv.index("--ttl")
        try:
            ttl = int(argv[i + 1])
            del argv[i:i + 2]
        except (IndexError, ValueError):
            print("error: --ttl needs an integer")
            return 2
    cmd = argv[0]
    rest = argv[1:]
    if cmd == "status":
        if len(rest) != 1:
            print("usage: loop-lease.py status <marker.md> [--ttl N]"); return 2
        return status(rest[0], ttl)
    if cmd in ("acquire", "refresh"):
        if len(rest) != 2:
            print(f"usage: loop-lease.py {cmd} <marker.md> <runner-id> [--ttl N]"); return 2
        return acquire(rest[0], rest[1], ttl) if cmd == "acquire" else refresh(rest[0], rest[1], ttl)
    if cmd == "release":
        if len(rest) != 2:
            print("usage: loop-lease.py release <marker.md> <runner-id>"); return 2
        return release(rest[0], rest[1])
    print(f"error: unknown command '{cmd}'")
    return 2


if __name__ == "__main__":
    sys.exit(main())
