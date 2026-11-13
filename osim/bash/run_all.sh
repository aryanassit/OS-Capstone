#!/usr/bin/env bash
# One-command demo: tests, then batch analysis on both datasets, then a log summary.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== [1/3] running test suite =="
python3 -m unittest discover -s tests -v 2>&1 | tail -n 6
echo "== [2/3] batch analysis =="
for ds in sample stress belady; do
  python3 main.py batch --input "data/${ds}_input.json" --out "outputs/${ds}"
done
echo "== [3/3] log summary =="
if [ -f logs/osim.log ]; then
  echo "log lines : $(wc -l < logs/osim.log)"
  echo "errors    : $(grep -c ' ERROR ' logs/osim.log || true)"
fi
echo "Done. See outputs/ for traces, CSVs and charts."
