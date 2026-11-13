#!/usr/bin/env python3
"""OSim - Operating System resource-management simulator.

Interactive:  python3 main.py
Scripted:     python3 main.py batch --input data/sample_input.json --out outputs/sample
              python3 main.py {sched|pages|alloc|banker|detect|disk|sysinfo|live} [--input FILE]
"""
import argparse
import os
import sys

from osim import runner, validation as V, bridge, reporting as R
from osim.errors import BridgeError, ValidationError
from osim.logger import get_logger
from osim.modules import scheduler

log = get_logger("main")
ROOT = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(ROOT, "data", "sample_input.json")


# ---------- safe input helpers ----------
def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        print()
        raise SystemExit(0)


def ask_ints(prompt):
    return [V.to_int(x, "value") for x in ask(prompt).replace(",", " ").split()]


def manual_processes():
    print("Enter processes as: pid arrival burst [priority]   (blank line to finish)")
    procs = []
    while True:
        line = ask(f"  process {len(procs) + 1}> ")
        if not line:
            break
        p = line.split()
        if len(p) not in (3, 4):
            print("  ! need 3 or 4 fields"); continue
        try:
            V.processes(procs + [{"pid": p[0], "arrival": p[1], "burst": p[2], "priority": p[3] if len(p) == 4 else 0}])
        except ValidationError as e:
            print(f"  ! {e}"); continue
        procs.append({"pid": p[0], "arrival": p[1], "burst": p[2], "priority": p[3] if len(p) == 4 else 0})
    return {"scheduling": {"processes": procs, "quantum": ask_ints("Time quantum: ")[0]}}


def manual_pages():
    return {"memory": {"reference_string": ask_ints("Reference string (e.g. 7 0 1 2 0 3): "),
                       "frames": ask_ints("Number of frames: ")[0], "max_frames": 7}}


def manual_alloc():
    parts = ask_ints("Partition sizes (e.g. 100 500 200): ")
    sizes = ask_ints("Process sizes   (e.g. 212 417 112): ")
    return {"memory": {"partitions": parts, "requests": [{"pid": f"M{i + 1}", "size": s} for i, s in enumerate(sizes)]}}


def manual_banker():
    avail = ask_ints("Available vector (e.g. 3 3 2): ")
    n = ask_ints("Number of processes: ")[0]
    mx, al = [], []
    for i in range(n):
        al.append(ask_ints(f"  P{i} allocation: "))
        mx.append(ask_ints(f"  P{i} max       : "))
    pid = ask_ints("Request from process index (-1 to skip): ")[0]
    d = {"available": avail, "max": mx, "allocation": al}
    if pid >= 0:
        d["request"] = {"pid": pid, "vector": ask_ints("Request vector: ")}
    return {"deadlock": d}


def manual_disk():
    return {"storage": {"requests": ask_ints("Request queue (e.g. 98 183 37): "),
                        "head": ask_ints("Head position: ")[0], "disk_size": ask_ints("Disk size (cylinders): ")[0],
                        "direction": ask("Direction (up/down) [up]: ") or "up"}}


def get_cfg(manual_fn, key):
    print("  Data source: 1) built-in sample  2) JSON file  3) type it in")
    c = ask("  choose> ")
    if c == "1":
        return runner.load_config(SAMPLE)
    if c == "2":
        return runner.load_config(ask("  path to JSON> "))
    if c == "3":
        return manual_fn()
    raise ValidationError("choose 1, 2 or 3")


# ---------- actions ----------
def act_sched(cfg=None):
    cfg = cfg or get_cfg(manual_processes, "scheduling")
    print(runner.run_scheduling(cfg)[1])


def act_pages(cfg=None):
    cfg = cfg or get_cfg(manual_pages, "memory")
    print(runner.run_pages(cfg)[1])


def act_alloc(cfg=None):
    cfg = cfg or get_cfg(manual_alloc, "memory")
    print(runner.run_alloc(cfg)[1])


def act_banker(cfg=None):
    cfg = cfg or get_cfg(manual_banker, "deadlock")
    print(runner.run_banker(cfg)[1])


def act_detect(cfg=None):
    cfg = cfg or runner.load_config(SAMPLE)
    print(runner.run_detection(cfg)[1])


def act_disk(cfg=None):
    cfg = cfg or get_cfg(manual_disk, "storage")
    print(runner.run_disk(cfg)[1])


def act_sysinfo(_=None):
    print(R.render_sysinfo(bridge.sysinfo()))


def act_live(_=None):
    n = V.to_int(ask("How many live processes (1-100) [8]: ") or 8, "count", 1, 100)
    procs = bridge.live_processes(n)
    print("(PIDs and nice values are real; burst is a proxy derived from RSS memory.)")
    print(R.table(["PID", "Arrival", "Burst", "Priority"], [[p["pid"], p["arrival"], p["burst"], p["priority"]] for p in procs]))
    print(R.render_schedule(scheduler.compare_all(procs, 3)))


def act_batch(_=None):
    inp = ask("Input JSON [data/sample_input.json]: ") or SAMPLE
    out = ask("Output folder [outputs/menu_run]: ") or os.path.join(ROOT, "outputs", "menu_run")
    print(runner.run_batch(runner.load_config(inp), out))
    print(f"Files written to {out}")


MENU = [("1", "CPU scheduling (FCFS/SJF/SRTF/RR/Priority)", act_sched),
        ("2", "Page replacement (FIFO/LRU/OPT + Belady check)", act_pages),
        ("3", "Memory allocation (first/best/worst fit)", act_alloc),
        ("4", "Deadlock avoidance (Banker's algorithm)", act_banker),
        ("5", "Deadlock detection", act_detect),
        ("6", "Disk scheduling (FCFS/SSTF/SCAN/C-SCAN/LOOK/C-LOOK)", act_disk),
        ("7", "Host system info (Bash bridge)", act_sysinfo),
        ("8", "Schedule REAL host processes (Bash bridge)", act_live),
        ("9", "Run everything + save report, CSVs, charts", act_batch)]


def menu():
    actions = {k: f for k, _, f in MENU}
    while True:
        print("\n" + "=" * 54 + "\n  OSim - OS Resource Management Simulator\n" + "=" * 54)
        for k, label, _ in MENU:
            print(f"  {k}) {label}")
        print("  0) Exit")
        c = ask("Select> ")
        if c == "0":
            log.info("menu exit")
            return 0
        if c not in actions:
            print("! Invalid choice, enter 0-9."); continue
        try:
            actions[c]()
        except ValidationError as e:
            log.error("validation: %s", e)
            print(f"\n[INPUT ERROR] {e}")
        except BridgeError as e:
            log.error("bridge: %s", e)
            print(f"\n[BASH ERROR] {e}")
        except KeyboardInterrupt:
            print("\n(cancelled)")
        except Exception as e:  # last resort: log with traceback, keep the menu alive
            log.exception("unexpected error")
            print(f"\n[UNEXPECTED ERROR] {type(e).__name__}: {e} (details in logs/osim.log)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    for name in ("sched", "pages", "alloc", "banker", "detect", "disk", "sysinfo", "live"):
        p = sub.add_parser(name)
        p.add_argument("--input", default=SAMPLE)
    b = sub.add_parser("batch")
    b.add_argument("--input", default=SAMPLE)
    b.add_argument("--out", default=os.path.join(ROOT, "outputs", "run"))
    args = ap.parse_args(argv)
    if not args.cmd:
        return menu()
    try:
        if args.cmd == "batch":
            print(runner.run_batch(runner.load_config(args.input), args.out))
            print(f"Files written to {args.out}")
        elif args.cmd == "sysinfo":
            act_sysinfo()
        elif args.cmd == "live":
            procs = bridge.live_processes(8)
            print(R.render_schedule(scheduler.compare_all(procs, 3)))
        else:
            fn = {"sched": act_sched, "pages": act_pages, "alloc": act_alloc,
                  "banker": act_banker, "detect": act_detect, "disk": act_disk}[args.cmd]
            fn(runner.load_config(args.input))
        return 0
    except (ValidationError, BridgeError) as e:
        log.error("%s: %s", args.cmd, e)
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        log.exception("unexpected error")
        print(f"UNEXPECTED ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
