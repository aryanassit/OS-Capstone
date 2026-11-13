# OSim - Operating-System Resource-Management Simulator

One integrated Python + Bash application that simulates five OS areas and compares algorithms with tables and charts.

| Area | Algorithms | File |
|---|---|---|
| CPU scheduling | FCFS, SJF, SRTF, Round Robin, Priority | `osim/modules/scheduler.py` |
| Memory | FIFO / LRU / Optimal page replacement (+ Belady's anomaly check); first / best / worst fit allocation | `osim/modules/memory.py` |
| Deadlock | Banker's safety + request algorithm; deadlock detection | `osim/modules/deadlock.py` |
| Storage | FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK disk scheduling | `osim/modules/storage.py` |
| Reporting | text tables, Gantt, CSV, matplotlib charts | `osim/reporting.py` |

## Requirements
- Linux/macOS/WSL, Python 3.8+, Bash
- `matplotlib` for charts only (`pip install matplotlib`). Without it, everything else still runs and charts are skipped.
- No other dependencies. Tests use the standard `unittest`.

## How to run
```bash
cd osim
python3 main.py                       # interactive menu
bash bash/run_all.sh                  # tests + batch on 3 datasets + log summary (the "demo" command)
bash bash/run_tests.sh                # tests only (36 tests)
python3 main.py batch --input data/sample_input.json --out outputs/sample
python3 main.py disk --input data/stress_input.json     # single module: sched|pages|alloc|banker|detect|disk
python3 main.py sysinfo               # host info through Bash
python3 main.py live                  # schedule real host processes through Bash
```
Exit codes: `0` ok, `2` bad input/Bash failure (message on stderr), `1` unexpected bug (traceback in log).
 cdcd 
## Menu
1 CPU scheduling - 2 Page replacement - 3 Memory allocation - 4 Banker's - 5 Deadlock detection - 6 Disk scheduling - 7 Host info (Bash) - 8 Schedule real host processes (Bash) - 9 Run everything and save report/CSV/charts.
Options 1-4 and 6 let you pick: built-in sample, your own JSON file, or typed input.

## Architecture / data flow
```
 data/*.json ──> runner.load_config ──> validation.py ──> modules/* (pure functions, return dicts)
 typed input ───────────────────────────────┘                      │
 bash/*.sh ──> bridge.py (subprocess) ──> process list ────────────┤
                                                                   v
                                         reporting.py ──> terminal tables / trace.txt / CSV / PNG charts
 logger.py: every run, input error and Bash call -> logs/osim.log
```
Design rules: modules never print or read input (so they are testable); all validation is in one file; all rendering is in one file.

## Bash integration (real, not decorative)
- `bash/sysinfo.sh` - reads `/proc` and `df`; Python parses it (menu 7, appended to every batch report).
- `bash/live_processes.sh N` - `ps` output for the N largest processes; Python turns it into a scheduling workload (menu 8). **PIDs and nice values are real; burst time is a proxy** derived from memory use, because `ps` cannot know future CPU burst.
- `bash/run_all.sh`, `bash/run_tests.sh` - orchestration.
- Bridge failures (no bash, timeout, bad argument) raise `BridgeError`, are logged, and never crash the menu.

## Input format (`data/sample_input.json`)
Sections `scheduling`, `memory`, `deadlock`, `storage` - see the file; it is the format reference.
Three datasets are included: `sample_input.json` (textbook values), `stress_input.json` (15 processes, 80 page refs, 30 disk requests, seed 42 - regenerate with `python3 data/make_stress.py`), `belady_input.json` (shows Belady's anomaly).

## Assumptions (important for correctness claims)
- Scheduling: lower priority number = higher priority; Priority is non-preemptive; context-switch cost is zero; ties broken by arrival then input order.
- SCAN / C-SCAN go to the physical disk edge. The C-SCAN/C-LOOK return jump **is counted** as head movement. LOOK / C-LOOK stop at the last request.
- Allocation is **fixed partitions**, one process per partition. "External fragmentation" here means free partitions left unused while some process failed to fit.
- Page replacement: OPT ties are broken by frame order.

## Evidence in this repo
- `outputs/<dataset>/trace.txt` - full output trace; `*.csv` - tables; `*.png` - charts
- `docs/terminal_*.png` - terminal renders (see warning below); `logs/osim.log` - activity log
- `docs/REPORT.md` - concise report

> **Warning:** `docs/terminal_*.png` are rendered from captured real output by `docs/make_terminal_renders.py`. They are not OS screenshots. Take your own screenshots of `python3 main.py` and `bash bash/run_all.sh` on your machine and add them to `docs/` before submitting.

## Tests (`tests/test_osim.py`, 36 tests)
- Textbook correctness: FCFS/SJF/SRTF/RR waiting times, 15/12/9 page faults, Belady 9->10, Banker safe sequence P1,P3,P4,P0,P2, disk totals 640/236/331/382/299/322.
- Invariants: turnaround = waiting + burst; OPT <= FIFO, LRU; every disk request served exactly once.
- Boundary: 1 process, quantum 1, quantum > burst, 1 frame, frames >= unique pages, head at disk edge, idle CPU gap.
- Invalid: empty lists, zero/negative/non-numeric values, duplicate or reserved PIDs, out-of-range cylinders, mismatched matrix sizes, allocation > max, unknown algorithm, missing/corrupt JSON, bad Bash argument, missing script, bad menu input (menu must not crash).
- Note: `logs/osim.log` shows a few ERROR lines after a test run. They come from the tests that deliberately feed bad input.

## Known limitations
- A typing mistake in manual entry cancels that action (back to menu) instead of re-asking the one field.
- CPU utilisation and throughput are identical across algorithms on these datasets (no I/O, no switch cost), so they do not discriminate between them.
- No paging tables/TLB, no dynamic partitioning or compaction, no file-system allocation (storage = disk scheduling only), no resource-allocation-graph drawing.
