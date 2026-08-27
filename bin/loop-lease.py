#!/usr/bin/env python3
"""loop-lease — an atomic single-runner lease for Loobster goal-loops.

The goal-loop must run only ONE instance per loop marker (so a ScheduleWakeup/cron
re-entry, or a parallel headless run, backs off instead of colliding). The marker
frontmatter (`runner` / `runnerHeartbeatAt`) is a human-readable mirror, but the
*authoritative* mutex is a lock file claimed atomically here with O_CREAT|O_EXCL —
so two processes racing to acquire cannot both win.

Lock file: `<marker>.lock`, containing `<runner-id>\n<epoch-seconds>`.

The <runner-id> MUST be unique per running instance -- generate one with `newid`
at the start of each invocation and reuse it for that instance's acquire/refresh/
release. Do NOT derive it from the goal/branch or reuse the marker's stored
`runner:`: a re-entry that reuses the live holder's id hits the "already held"
path and mistakes the live lease for its own, defeating the mutex.

Usage:
  loop-lease.py newid                                       # print a fresh unique runner id
  loop-lease.py acquire <marker.md> <runner-id> [--ttl N]   # claim or take over a stale lease
  loop-lease.py refresh <marker.md> <runner-id> [--ttl N]   # bump the heartbeat (must hold it)
  loop-lease.py release <marker.md> <runner-id>             # release (must hold it)
  loop-lease.py status  <marker.md>          [--ttl N]      # report holder + freshness

Exit codes:
  0  success (acquired / refreshed / released / status printed)
  3  lease is held by a live (fresh) runner that is not you  -> back off and exit
  2  usage error

Default TTL is 3600s. It must exceed the LONGEST realistic cycle, not the shortest:
the lease is only refreshed at cycle boundaries, and a single act step (a full /run
in a subagent) can hold the runner silent for 30-60 minutes. A TTL shorter than a
cycle makes a live runner look stale mid-act, so a cron/wakeup re-entry "takes over"
and two instances collide on the same worktree. The cost of a long TTL is slower
takeover after a hard crash (bounded by TTL + re-entry cadence); pass --ttl to tune.
"""
import fcntl
import os
import sys
import time

DEFAULT_TTL = 3600


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
        f.write(f"{runner}\n{int(time.time())}\n")
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
    return _take_over_stale(path, runner, ttl, holder, ts)


def _take_over_stale(path, runner, ttl, holder, ts):
    """Take over a lease we observed as stale -- with EXACTLY one winner under a race.

    The old code did os.remove()+O_EXCL-create, which double-wins: two runners both
    see it stale, A removes+creates, then B's *blind* os.remove() deletes A's fresh
    lock and B re-creates -- both return 0, so two runners drive the same loop.

    We serialize the break with an flock on a gate file. flock is exclusive AND is
    released by the OS when the holder's fd closes -- including on crash -- so there
    is no orphaned-lock problem to reason about (unlike a plain lock *file*, whose
    stale-cleanup is itself a race). Under the flock we re-read the lease: if a prior
    taker already refreshed it we yield; otherwise we alone break the stale lock and
    write a fresh one via an atomic tmp+os.replace (the path is never momentarily
    empty). Deterministic single winner; crash-safe with no timeout/self-heal needed.
    """
    gate = path + ".steal"
    fd = os.open(gate, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)          # blocks; exactly one holder at a time
        cur_holder, cur_ts = _read_lock(path)   # re-read under the flock
        if cur_holder and cur_holder != runner and _fresh(cur_ts, ttl):
            print(f"held by {cur_holder} (age {int(time.time() - cur_ts)}s)")
            return 3
        _force_write(path, runner)
        print(f"acquired {runner} (took over stale lease from {holder})")
        return 0
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _force_write(path, runner):
    # Per-pid tmp so a takeover's write can't collide with an incumbent's concurrent
    # refresh on a shared tmp name (which raced to an unhandled FileNotFoundError on
    # the second os.replace). Each writer replaces atomically from its own tmp.
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(f"{runner}\n{int(time.time())}\n")
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
    if cmd == "newid":
        # host-pid-epoch-rand: unique per invocation without needing coordination.
        print(f"{os.uname().nodename.split('.')[0]}-{os.getpid()}-{int(time.time())}-"
              f"{os.urandom(3).hex()}")
        return 0
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
