#!/usr/bin/env bash
# Prints real host resource facts as key=value lines. Consumed by osim/bridge.py.
set -euo pipefail
echo "hostname=$(hostname)"
echo "kernel=$(uname -sr)"
echo "cpu_cores=$(nproc 2>/dev/null || echo 1)"
if [ -r /proc/loadavg ]; then
  read -r l1 l5 l15 _ < /proc/loadavg
  echo "load_1m=$l1"; echo "load_5m=$l5"; echo "load_15m=$l15"
fi
if [ -r /proc/meminfo ]; then
  awk '/^MemTotal/{t=$2} /^MemAvailable/{a=$2} END{printf "mem_total_kb=%d\nmem_available_kb=%d\n", t, a}' /proc/meminfo
fi
df -Pk / | awk 'NR==2{gsub("%","",$5); printf "disk_total_kb=%d\ndisk_used_kb=%d\ndisk_use_pct=%s\n", $2, $3, $5}'
