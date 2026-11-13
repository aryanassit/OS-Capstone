"""Reporting: plain-text tables/traces (no dependencies), CSV export, and matplotlib charts."""
import csv
import os

from .logger import get_logger

log = get_logger("report")


def table(headers, rows):
    rows = [[str(c) for c in r] for r in rows]
    w = [max(len(str(h)), *(len(r[i]) for r in rows)) if rows else len(str(h)) for i, h in enumerate(headers)]
    line = "+" + "+".join("-" * (x + 2) for x in w) + "+"
    fmt = lambda r: "| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |"
    return "\n".join([line, fmt(headers), line, *(fmt(r) for r in rows), line])


def banner(title):
    return f"\n{'=' * 72}\n {title}\n{'=' * 72}"


def gantt_text(gantt, width_per_unit=1, max_cols=100):
    total = gantt[-1][2]
    scale = 1 if total <= max_cols else max_cols / total
    bar, ticks = "|", " "
    for pid, s, e in gantt:
        cell = max(len(pid) + 2, int(round((e - s) * scale)) * width_per_unit)
        bar += pid.center(cell) + "|"
        ticks += str(s).ljust(cell + 1)
    return bar + "\n" + ticks + str(gantt[-1][2])


def render_schedule(results):
    out = [banner("CPU SCHEDULING")]
    for algo, r in results.items():
        out.append(f"\n-- {algo} --\n{gantt_text(r['gantt'])}")
        out.append(table(["PID", "Arr", "Burst", "Prio", "Done", "TAT", "Wait", "Resp"],
                         [[x["pid"], x["arrival"], x["burst"], x["priority"], x["completion"],
                           x["turnaround"], x["waiting"], x["response"]] for x in r["rows"]]))
    out.append("\nSUMMARY (lower is better except CPU% and throughput)")
    out.append(table(["Algorithm", "AvgWait", "AvgTAT", "AvgResp", "CPU%", "Thruput", "CtxSw"],
                     [[a, r["avg_waiting"], r["avg_turnaround"], r["avg_response"],
                       r["cpu_utilization"], r["throughput"], r["context_switches"]]
                      for a, r in results.items()]))
    best = min(results, key=lambda a: results[a]["avg_waiting"])
    out.append(f"Lowest average waiting time: {best} ({results[best]['avg_waiting']})")
    return "\n".join(out)


def render_pages(results, refs, frames, curve=None, anomalies=None, show_trace=True):
    out = [banner(f"PAGE REPLACEMENT  (frames={frames}, references={len(refs)})")]
    if show_trace:
        for algo, r in results.items():
            out.append(f"\n-- {algo} trace --")
            out.append(table(["Step", "Page", "Frames", "Result", "Evicted"],
                             [[t["step"], t["page"], " ".join(map(str, t["frames"])),
                               "FAULT" if t["fault"] else "hit",
                               "-" if t["evicted"] is None else t["evicted"]] for t in r["trace"]]))
    out.append("\nSUMMARY")
    out.append(table(["Algorithm", "Faults", "Hits", "Fault%", "Hit%"],
                     [[a, r["faults"], r["hits"], r["fault_rate"], r["hit_ratio"]] for a, r in results.items()]))
    if curve:
        n = len(curve["FIFO"])
        out.append("\nFAULTS vs FRAME COUNT")
        out.append(table(["Frames"] + list(curve),
                         [[f + 1] + [curve[a][f] for a in curve] for f in range(n)]))
        if anomalies:
            out.append("Belady's anomaly detected (FIFO faults INCREASE with more frames): " +
                       ", ".join(f"{a}->{a + 1} frames: {x}->{y} faults" for a, x, y in anomalies))
        else:
            out.append("No Belady's anomaly in this reference string.")
    return "\n".join(out)


def render_alloc(results, partitions):
    out = [banner(f"CONTIGUOUS (FIXED-PARTITION) ALLOCATION  partitions={partitions}")]
    for s, r in results.items():
        out.append(f"\n-- {s.upper()} FIT --")
        out.append(table(["PID", "Size", "Partition#", "PartSize", "Wasted"],
                         [[p["pid"], p["size"], p["partition"], p["partition_size"], p["waste"]] for p in r["placed"]]
                         or [["-"] * 5]))
        out.append(f"Not allocated: {', '.join(r['failed']) or 'none'}")
    out.append("\nSUMMARY")
    out.append(table(["Strategy", "Placed", "Failed", "InternalFrag", "ExternalFrag", "Util%"],
                     [[s, len(r["placed"]), len(r["failed"]), r["internal_frag"], r["external_frag"],
                       r["utilization"]] for s, r in results.items()]))
    return "\n".join(out)


def render_banker(safety, req_result=None, req_text=""):
    out = [banner("DEADLOCK AVOIDANCE: BANKER'S ALGORITHM")]
    out.append("Need matrix (max - allocation):")
    out.append(table(["Proc"] + [f"R{j}" for j in range(len(safety["need"][0]))],
                     [[f"P{i}"] + r for i, r in enumerate(safety["need"])]))
    if safety["safe"]:
        out.append("State is SAFE. Safe sequence: " + " -> ".join(safety["sequence"]))
        out.append(table(["Run", "Work before"], [[s["pid"], s["work_before"]] for s in safety["steps"]]))
    else:
        out.append("State is UNSAFE. Cannot finish: " + ", ".join(safety["unfinished"]))
    if req_result:
        verdict = "GRANTED" if req_result["granted"] else "DENIED"
        out.append(f"\nResource request {req_text}: {verdict} - {req_result['reason']}")
        if req_result.get("sequence"):
            out.append("Safe sequence after grant: " + " -> ".join(req_result["sequence"]))
    return "\n".join(out)


def render_detection(res):
    out = [banner("DEADLOCK DETECTION")]
    out.append("DEADLOCK FOUND. Deadlocked processes: " + ", ".join(res["processes"]) if res["deadlocked"]
               else "No deadlock. Every process can finish.")
    return "\n".join(out)


def render_disk(results, head, size):
    out = [banner(f"DISK SCHEDULING  (head={head}, disk size={size})")]
    for a, r in results.items():
        out.append(f"{a:6} total={r['total_movement']:>6}  avg seek={r['avg_seek']:>7}  path: "
                   + " ".join(map(str, r["path"][:14])) + (" ..." if len(r["path"]) > 14 else ""))
    out.append("\nSUMMARY")
    out.append(table(["Algorithm", "TotalMovement", "AvgSeek"],
                     [[a, r["total_movement"], r["avg_seek"]] for a, r in results.items()]))
    best = min(results, key=lambda a: results[a]["total_movement"])
    out.append(f"Least head movement: {best} ({results[best]['total_movement']})")
    out.append("Note: SSTF can starve far-away requests; SCAN family gives bounded waiting.")
    return "\n".join(out)


def render_sysinfo(info):
    return banner("HOST SYSTEM (via bash/sysinfo.sh)") + "\n" + table(["Key", "Value"], [[k, v] for k, v in info.items()])


# ---------- files ----------
def write_csv(path, headers, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(headers)
        w.writerows(rows)
    log.info("wrote %s", path)


def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        log.warning("matplotlib missing: charts skipped")
        return None


def _save(plt, fig, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    log.info("chart %s", path)
    return path


def chart_schedule(results, path):
    plt = _plt()
    if not plt:
        return None
    algos = list(results)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    w = 0.26
    for k, (key, label) in enumerate([("avg_waiting", "Avg waiting"), ("avg_turnaround", "Avg turnaround"),
                                      ("avg_response", "Avg response")]):
        ax.bar([i + (k - 1) * w for i in range(len(algos))], [results[a][key] for a in algos], w, label=label)
    ax.set_xticks(range(len(algos)))
    ax.set_xticklabels(algos)
    ax.set_ylabel("Time units")
    ax.set_title("CPU scheduling: time metrics by algorithm (lower is better)")
    ax.legend()
    return _save(plt, fig, path)


def chart_gantt(results, path):
    plt = _plt()
    if not plt:
        return None
    pids = sorted({g[0] for r in results.values() for g in r["gantt"] if g[0] != "IDLE"},
                  key=lambda x: (len(x), x))
    cmap = plt.get_cmap("tab20")
    col = {p: cmap(i % 20) for i, p in enumerate(pids)}
    fig, axes = plt.subplots(len(results), 1, figsize=(9, 1.3 * len(results) + 0.8), sharex=True)
    axes = [axes] if len(results) == 1 else axes
    for ax, (algo, r) in zip(axes, results.items()):
        for pid, s, e in r["gantt"]:
            ax.barh(0, e - s, left=s, color="#dddddd" if pid == "IDLE" else col[pid], edgecolor="black")
            if e - s >= 2 and pid != "IDLE":
                ax.text((s + e) / 2, 0, pid, ha="center", va="center", fontsize=7)
        ax.set_yticks([])
        ax.set_ylabel(algo, rotation=0, ha="right", va="center")
    axes[-1].set_xlabel("Time")
    axes[0].set_title("Gantt charts by algorithm")
    return _save(plt, fig, path)


def chart_pages(curve, path):
    plt = _plt()
    if not plt:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for a, v in curve.items():
        ax.plot(range(1, len(v) + 1), v, marker="o", label=a)
    ax.set_xlabel("Number of frames")
    ax.set_ylabel("Page faults")
    ax.set_title("Page faults vs frames (FIFO bump = Belady's anomaly)")
    ax.legend()
    ax.grid(alpha=0.3)
    return _save(plt, fig, path)


def chart_disk(results, path):
    plt = _plt()
    if not plt:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.5))
    names = list(results)
    vals = [results[a]["total_movement"] for a in names]
    bars = ax.bar(names, vals, color="#4c78a8")
    ax.bar_label(bars)
    ax.set_ylabel("Total head movement (cylinders)")
    ax.set_title("Disk scheduling: total head movement (lower is better)")
    return _save(plt, fig, path)


def chart_alloc(results, path):
    plt = _plt()
    if not plt:
        return None
    names = list(results)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar([i - 0.2 for i in range(3)], [results[n]["internal_frag"] for n in names], 0.4, label="Internal fragmentation")
    ax.bar([i + 0.2 for i in range(3)], [results[n]["external_frag"] for n in names], 0.4, label="Unusable free space")
    ax.set_xticks(range(3))
    ax.set_xticklabels([n + " fit" for n in names])
    ax.set_ylabel("Memory units")
    ax.set_title("Allocation strategy: fragmentation")
    ax.legend()
    return _save(plt, fig, path)
