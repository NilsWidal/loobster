#!/usr/bin/env bash
# loobster-drive — an EXTERNAL driver that keeps a goal-loop alive from outside
# the agent, by re-invoking an agent CLI until the loop's marker leaves `active`.
#
# Why it exists: in-agent self-driving (ScheduleWakeup / CronCreate / the Stop
# hook) only works where those facilities exist — Claude Code. Codex and Cursor
# have no Stop hook and no scheduler, and even in Claude Code a hard-killed
# session can leave nothing armed. This script is the durability layer that works
# EVERYWHERE, because it supplies the turns itself: while `plans/loop/<slug>.md`
# says `status: active`, it re-invokes the agent CLI with the loop prompt; the
# loop's own self-healing (lease + heartbeats + checkpoint) makes each re-entry
# safe and idempotent. A `paused` marker (human approval gate) STOPS the driver —
# it never supplies turns past a gate.
#
#   bin/loobster-drive.sh plans/loop/<slug>.md [options]
#
# Options:
#   --tool claude|codex|cursor   agent CLI to drive (default: claude)
#   --prompt "<text>"            override the re-entry prompt
#                                (default: built from the marker's `goal:` —
#                                 claude: "/loobster:loop <goal>", codex: "$loop <goal>",
#                                 cursor: "/loobster:loop <goal>")
#   --interval N                 seconds between invocations (default 30)
#   --max N                      max invocations before giving up (default 50)
#   -n | --dry-run               print what would run, don't invoke
#
# Custom CLI: set LOOBSTER_DRIVE_CMD with a {prompt} placeholder, e.g.
#   LOOBSTER_DRIVE_CMD='mytool run --message {prompt}'
# The placeholder is replaced with "$LOOBSTER_PROMPT" (an exported env var), not
# the raw text — so goals containing quotes/;/$ can't break or inject into the
# command line.
#
# Permissions note (deliberate): this script does NOT inject permission-bypass
# flags. Configure your agent for unattended runs yourself (e.g. Claude Code
# `permissions.defaultMode` + a deny list) — an external driver silently adding
# `--dangerously-skip-permissions` would be a guardrail bypass, not a feature.
set -u

MARKER="" TOOL="claude" PROMPT="" INTERVAL=30 MAX=50 DRY=0
needval(){ [ "$2" -ge 2 ] || { echo "error: $1 needs a value"; exit 2; }; }
while [ $# -gt 0 ]; do
  case "$1" in
    --tool)     needval "$1" $#; TOOL="$2"; shift 2 ;;
    --prompt)   needval "$1" $#; PROMPT="$2"; shift 2 ;;
    --interval) needval "$1" $#; INTERVAL="$2"; shift 2 ;;
    --max)      needval "$1" $#; MAX="$2"; shift 2 ;;
    -n|--dry-run) DRY=1; shift ;;
    -h|--help)  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$0"; exit 0 ;;
    -*)         echo "error: unknown option $1 (see --help)"; exit 2 ;;
    *)          MARKER="$1"; shift ;;
  esac
done
[ -n "$MARKER" ] || { echo "usage: loobster-drive.sh <plans/loop/slug.md> [options] (see --help)"; exit 2; }
[ -f "$MARKER" ] || { echo "error: marker not found: $MARKER"; exit 2; }
case "$INTERVAL$MAX" in *[!0-9]*) echo "error: --interval/--max need integers"; exit 2 ;; esac

frontmatter_field(){ # frontmatter_field <key> — value from the marker's first fence
  awk -v key="$2" '
    /^---[[:space:]]*$/ { fences++; next }
    fences == 1 && $0 ~ "^[[:space:]]*" key "[[:space:]]*:" {
      sub("^[[:space:]]*" key "[[:space:]]*:[[:space:]]*", ""); print; exit }
    fences >= 2 { exit }' "$1"
}

status(){ frontmatter_field "$MARKER" status | tr '[:upper:]' '[:lower:]'; }

if [ -z "$PROMPT" ]; then
  goal="$(frontmatter_field "$MARKER" goal)"
  [ -n "$goal" ] || { echo "error: marker has no goal: field; pass --prompt"; exit 2; }
  case "$TOOL" in
    codex) PROMPT="\$loop $goal" ;;
    *)     PROMPT="/loobster:loop $goal" ;;
  esac
fi

invoke(){
  if [ -n "${LOOBSTER_DRIVE_CMD:-}" ]; then
    # Substitute a QUOTED env reference, never the raw goal text: a goal like
    # "don't stop; rm x" must arrive as one argument, not as shell syntax.
    export LOOBSTER_PROMPT="$PROMPT"
    local cmd="${LOOBSTER_DRIVE_CMD//\{prompt\}/\"\$LOOBSTER_PROMPT\"}"
    sh -c "$cmd"
  else
    case "$TOOL" in
      claude) claude -p "$PROMPT" ;;
      codex)  codex exec "$PROMPT" ;;
      cursor) cursor-agent -p "$PROMPT" ;;
      *)      echo "error: unknown --tool '$TOOL' (claude|codex|cursor, or LOOBSTER_DRIVE_CMD)"; return 2 ;;
    esac
  fi
}

LOG="$MARKER.drive.log"
say(){ echo "[loobster-drive] $1"; echo "$(date '+%Y-%m-%dT%H:%M:%S') $1" >> "$LOG"; }

say "driving $MARKER via $TOOL every ${INTERVAL}s (max $MAX runs); prompt: $PROMPT"
i=0
while :; do
  st="$(status)"
  case "$st" in
    active) ;;
    paused) say "marker is PAUSED — a human approval gate is pending. Stopping; answer the gate, set status: active, then re-run this driver."; exit 0 ;;
    done)   say "marker is DONE — loop finished. Stopping."; exit 0 ;;
    *)      say "marker status is '$st' (not active) — stopping."; exit 0 ;;
  esac
  if [ "$i" -ge "$MAX" ]; then
    say "reached --max $MAX invocations without the loop exiting — stopping (raise --max to continue)."
    exit 1
  fi
  i=$((i + 1))
  if [ "$DRY" = 1 ]; then
    say "dry-run $i/$MAX: would invoke $TOOL with: $PROMPT"
    exit 0
  fi
  say "run $i/$MAX: invoking $TOOL"
  invoke; rc=$?
  say "run $i/$MAX: $TOOL exited $rc"
  sleep "$INTERVAL"
done
