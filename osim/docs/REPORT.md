# OSim - Concise Report

## 1. Problem and design (Phase 1)
Goal: one program that simulates the main OS resource managers and compares algorithms on the same inputs.
Modules: scheduler, memory, deadlock, storage, reporting, plus validation, logging and a Bash bridge.
Data design: every module takes plain lists/dicts and returns plain dicts (Gantt = list of `(pid,start,end)`, trace = list of per-step dicts). That keeps modules testable and lets one `runner` feed both the menu and batch mode.

## 2. Implementation (Phase 2)
Five areas, 21 algorithm variants, menu + scripted CLI, two Bash helpers integrated through `subprocess`. See README for the map.

## 3. Results (Phase 3)
Datasets: **sample** (4 processes, textbook), **stress** (15 processes, 80 page references, 30 disk requests, seed 42), **belady**.
Charts: `outputs/*/scheduling_metrics.png`, `scheduling_gantt.png`, `page_faults_vs_frames.png`, `disk_head_movement.png`, `allocation_fragmentation.png`.

**CPU scheduling - average waiting time (lower is better)**

| Dataset | FCFS | SJF | SRTF | RR | Priority |
|---|---|---|---|---|---|
| sample (q=4) | 8.75 | 7.75 | **6.50** | 11.75 | 7.75 |
| stress (q=4) | 60.47 | 42.40 | **41.27** | 88.00 | 52.73 |

Average response time on stress: RR **19.33**, SRTF 40.20, SJF 42.40, Priority 52.73, FCFS 60.47. Context switches on stress: RR 48 vs 14 for FCFS/SJF/Priority.
Observations:
- SRTF/SJF minimise waiting; this matches theory (shortest-first is optimal for average waiting).
- RR is worst for waiting but best for response. It trades total waiting for interactivity, and costs 3x the context switches. Switch cost is not modelled, so RR looks cheaper here than it would on real hardware.
- On `sample`, Priority equals SJF only because the priorities happen to follow burst order. It is not a general result.
- SRTF and SJF can starve long jobs (P9 and P4 finish last on stress). We did not measure max waiting; this is stated from the Gantt chart.

**Page replacement - faults (lower is better)**

| Dataset | Frames | FIFO | LRU | OPT |
|---|---|---|---|---|
| sample (20 refs) | 3 | 15 | 12 | 9 |
| stress (80 refs) | 4 | 32 | 30 | 21 |
| belady (12 refs) | 3 -> 4 | 9 -> **10** | 10 -> 8 | 7 -> 6 |

- OPT is the lower bound in all runs (also asserted in tests). LRU is close to FIFO on stress (30 vs 32) because the stress string has only mild locality.
- Belady's anomaly is reproduced: FIFO gets *worse* going from 3 to 4 frames. LRU and OPT cannot show it (stack algorithms).

**Allocation (fixed partitions)**

| Dataset | Strategy | Placed | Internal waste | Util % |
|---|---|---|---|---|
| sample (4 req) | first / best / worst | 3 / **4** / 3 | 559 / 433 / 659 | 43.6 / **68.7** / 43.6 |
| stress (10 req) | first / best / worst | 7 / **8** / 6 | 532 / 395 / 716 | 56.8 / **68.8** / 45.0 |

Best fit placed the most processes in both datasets. Worst fit was worst in both. Caveat: this is two datasets, not a general proof; best fit is not always best.

**Disk scheduling - total head movement (lower is better)**

| Dataset | FCFS | SSTF | SCAN | C-SCAN | LOOK | C-LOOK |
|---|---|---|---|---|---|---|
| sample (head 53, 200 cyl) | 640 | **236** | 331 | 382 | 299 | 322 |
| stress (head 250, 500 cyl) | 4195 | 727 | 723 | 997 | **715** | 939 |

- FCFS moves the head 2-3x more than the seek-aware methods on the small sample and about 6x more on stress (4195 vs 715-727 for the best three).
- SSTF wins on the small sample but LOOK/SCAN beat it on stress. SSTF can starve distant requests; the SCAN family bounds waiting.
- C-SCAN/C-LOOK look worse on total movement because the return jump is counted. Their benefit (more uniform wait) is not measured here.

**Deadlock**
- sample: state is safe, sequence P1,P3,P4,P0,P2; P1 request (1,0,2) granted; detection finds P1,P2,P3,P4 deadlocked.
- stress: initial state is **unsafe**; P0 request (1,0,0,1) denied; detection finds P0,P1,P2,P3,P5 deadlocked (P4 can finish).

## 4. Testing and reliability (Phase 4)
36 automated tests, all passing (`bash bash/run_tests.sh`): textbook values, invariants, boundary cases, invalid input, Bash failures, CLI exit codes, menu robustness. Custom exceptions (`ValidationError`, `BridgeError`) separate user mistakes from bugs. All activity and errors go to `logs/osim.log`. Two bugs were found and fixed during testing: C-SCAN did not run to the disk edge when no lower requests existed (inconsistent with SCAN), and one test used the wrong textbook state.

## 5. Limitations
See README. Main ones: no switch cost or I/O in scheduling, fixed partitions only, live-process burst is a proxy, manual entry has no per-field retry.
