"""CPU scheduling: FCFS, SJF, SRTF, Round Robin, Priority (non-preemptive; lower number = higher priority)."""
from collections import deque
from .. import validation as V

IDLE = "IDLE"


def _merge(gantt):
    out = []
    for pid, s, e in gantt:
        if out and out[-1][0] == pid and out[-1][2] == s:
            out[-1] = (pid, out[-1][1], e)
        else:
            out.append((pid, s, e))
    return out


def _nonpreemptive(procs, key):
    pending = list(enumerate(procs))
    t, gantt = 0, []
    while pending:
        ready = [(i, p) for i, p in pending if p["arrival"] <= t]
        if not ready:
            nxt = min(p["arrival"] for _, p in pending)
            gantt.append((IDLE, t, nxt))
            t = nxt
            continue
        i, p = min(ready, key=lambda x: key(x[0], x[1]))
        gantt.append((p["pid"], t, t + p["burst"]))
        t += p["burst"]
        pending.remove((i, p))
    return gantt


def fcfs(procs, **_):
    return _nonpreemptive(procs, lambda i, p: (p["arrival"], i))


def sjf(procs, **_):
    return _nonpreemptive(procs, lambda i, p: (p["burst"], p["arrival"], i))


def priority(procs, **_):
    return _nonpreemptive(procs, lambda i, p: (p["priority"], p["arrival"], i))


def srtf(procs, **_):
    rem = {p["pid"]: p["burst"] for p in procs}
    order = {p["pid"]: i for i, p in enumerate(procs)}
    t, gantt, done = 0, [], 0
    while done < len(procs):
        ready = [p for p in procs if p["arrival"] <= t and rem[p["pid"]] > 0]
        if not ready:
            nxt = min(p["arrival"] for p in procs if rem[p["pid"]] > 0)
            gantt.append((IDLE, t, nxt))
            t = nxt
            continue
        p = min(ready, key=lambda p: (rem[p["pid"]], p["arrival"], order[p["pid"]]))
        gantt.append((p["pid"], t, t + 1))
        rem[p["pid"]] -= 1
        t += 1
        if rem[p["pid"]] == 0:
            done += 1
    return _merge(gantt)


def round_robin(procs, quantum=2, **_):
    q = V.quantum(quantum)
    order = sorted(range(len(procs)), key=lambda i: (procs[i]["arrival"], i))
    rem = {p["pid"]: p["burst"] for p in procs}
    queue, gantt, t, nxt = deque(), [], 0, 0

    def admit(upto):
        nonlocal nxt
        while nxt < len(order) and procs[order[nxt]]["arrival"] <= upto:
            queue.append(procs[order[nxt]])
            nxt += 1

    admit(0)
    while queue or nxt < len(order):
        if not queue:
            na = procs[order[nxt]]["arrival"]
            gantt.append((IDLE, t, na))
            t = na
            admit(t)
            continue
        p = queue.popleft()
        run = min(q, rem[p["pid"]])
        gantt.append((p["pid"], t, t + run))
        t += run
        rem[p["pid"]] -= run
        admit(t)
        if rem[p["pid"]] > 0:
            queue.append(p)
    return _merge(gantt)


ALGORITHMS = {"FCFS": fcfs, "SJF": sjf, "SRTF": srtf, "RR": round_robin, "PRIORITY": priority}


def metrics(procs, gantt):
    first, done = {}, {}
    for pid, s, e in gantt:
        if pid != IDLE:
            first.setdefault(pid, s)
            done[pid] = e
    rows = []
    for p in procs:
        ct = done[p["pid"]]
        tat = ct - p["arrival"]
        rows.append({"pid": p["pid"], "arrival": p["arrival"], "burst": p["burst"],
                     "priority": p["priority"], "completion": ct, "turnaround": tat,
                     "waiting": tat - p["burst"], "response": first[p["pid"]] - p["arrival"]})
    n = len(rows)
    makespan = max(r["completion"] for r in rows)
    busy = sum(e - s for pid, s, e in gantt if pid != IDLE)
    run = [g[0] for g in gantt if g[0] != IDLE]
    switches = sum(1 for a, b in zip(run, run[1:]) if a != b)
    avg = lambda k: round(sum(r[k] for r in rows) / n, 2)
    return {"rows": rows, "gantt": gantt, "avg_waiting": avg("waiting"),
            "avg_turnaround": avg("turnaround"), "avg_response": avg("response"),
            "cpu_utilization": round(100 * busy / makespan, 2),
            "throughput": round(n / makespan, 4), "context_switches": switches,
            "makespan": makespan}


def simulate(procs, algo, quantum=2):
    procs = V.processes(procs)
    algo = algo.upper()
    if algo not in ALGORITHMS:
        raise V.ValidationError(f"unknown algorithm {algo}; choose from {', '.join(ALGORITHMS)}")
    return metrics(procs, ALGORITHMS[algo](procs, quantum=quantum))


def compare_all(procs, quantum=2):
    procs = V.processes(procs)
    return {a: metrics(procs, f(procs, quantum=quantum)) for a, f in ALGORITHMS.items()}
