#!/usr/bin/env bash
# Usage: live_processes.sh [N]  -> CSV "pid,nice,rss_kb,command" for the N largest-memory processes.
set -euo pipefail
n="${1:-8}"
[[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -ge 1 ] && [ "$n" -le 100 ] || { echo "N must be 1-100" >&2; exit 2; }
ps -eo pid=,ni=,rss=,comm= --sort=-rss | head -n "$n" | awk '{printf "%s,%s,%s,%s\n",$1,($2=="-"?0:$2),$3,$4}'
