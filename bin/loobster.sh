#!/usr/bin/env bash
# 🦞 Loobster — the loop + lobster mascot of RePPIT.
# Animated red ASCII lobster whose claws clack while the loop spins.
#
#   ./bin/loobster.sh           # animate (Ctrl-C to stop, auto-stops after a while)
#   ./bin/loobster.sh --still   # print one frame and exit (no animation)
#   CYCLES=20 ./bin/loobster.sh # custom number of claw-clacks
set -u

RED=$'\033[1;31m'; DIM=$'\033[0;31m'; RST=$'\033[0m'; CLR=$'\033[H\033[2J'
SPIN='|/-\'

# Frame A — claws open
read -r -d '' A <<'EOF'
     \v/             \v/
    ( \ \           / / )
     \ \ \   ___   / / /
      \ \ \ (o o) / / /
       \ '--( L )--' /
       \\\ \|||/ ///
        \\ )|||( //
           (_/ \_)
EOF

# Frame B — claws SNAP
read -r -d '' B <<'EOF'
      v               v
     ( )             ( )
      \ \    ___    / /
       \ \  (o o)  / /
    >====( L )====<
       \\\ \|||/ ///
        \\ )|||( //
           (_/ \_)
EOF

banner(){ printf '%s          L O O B S T E R%s\n' "$RED" "$RST"; }

if [ "${1:-}" = "--still" ]; then
  printf '%s%s%s\n' "$RED" "$A" "$RST"; banner; exit 0
fi

cycles="${CYCLES:-12}"
[[ "$cycles" =~ ^[0-9]+$ ]] || cycles=12     # ignore a non-numeric CYCLES
trap 'printf "\033[?25h"; echo' EXIT         # restore cursor on exit
printf '\033[?25l'                          # hide cursor
i=0
while [ "$i" -lt "$cycles" ]; do
  frame=$([ $((i % 2)) -eq 0 ] && echo "$A" || echo "$B")
  sp=${SPIN:i%4:1}
  printf '%s%s%s%s\n' "$CLR" "$RED" "$frame" "$RST"
  printf '%s        L O O B S T E R%s   %s%s the loop that ships%s\n' "$RED" "$RST" "$DIM" "$sp" "$RST"
  sleep 0.35
  i=$((i + 1))
done
