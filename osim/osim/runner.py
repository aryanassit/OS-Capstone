"""Glue: runs each module from a config section and returns (results, rendered_text). Used by CLI menu and batch mode."""
import json
import os

from . import validation as V
from .errors import ValidationError
from .logger import get_logger
from .modules import deadlock, memory, scheduler, storage
from . import reporting as R

log = get_logger("runner")


def load_config(path):
    if not os.path.isfile(path):
        raise ValidationError(f"input file not found: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(f"{path} is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise ValidationError("top level of input JSON must be an object")
    log.info("loaded config %s", path)
    return data


def section(cfg, name):
    if name not in cfg or not isinstance(cfg[name], dict):
        raise ValidationError(f"input is missing the '{name}' section")
    return cfg[name]


def run_scheduling(cfg, out_dir=None):
    s = section(cfg, "scheduling")
    res = scheduler.compare_all(s.get("processes"), s.get("quantum", 2))
    log.info("scheduling run: %d procs, best wait=%s", len(s["processes"]),
             min(res, key=lambda a: res[a]["avg_waiting"]))
    if out_dir:
        R.write_csv(os.path.join(out_dir, "scheduling_summary.csv"),
                    ["algorithm", "avg_waiting", "avg_turnaround", "avg_response", "cpu_util", "throughput", "ctx_switches"],
                    [[a, r["avg_waiting"], r["avg_turnaround"], r["avg_response"], r["cpu_utilization"],
                      r["throughput"], r["context_switches"]] for a, r in res.items()])
        R.chart_schedule(res, os.path.join(out_dir, "scheduling_metrics.png"))
        R.chart_gantt(res, os.path.join(out_dir, "scheduling_gantt.png"))
    return res, R.render_schedule(res)


def run_pages(cfg, out_dir=None, show_trace=True):
    m = section(cfg, "memory")
    refs, frames = V.page_input(m.get("reference_string"), m.get("frames"))
    res = memory.compare_pages(refs, frames)
    curve = memory.fault_curve(refs, m.get("max_frames", 7))
    anomalies = memory.belady_anomaly(curve)
    log.info("page replacement run: faults=%s", {a: r["faults"] for a, r in res.items()})
    if out_dir:
        R.write_csv(os.path.join(out_dir, "page_replacement_summary.csv"), ["algorithm", "faults", "hits", "fault_pct"],
                    [[a, r["faults"], r["hits"], r["fault_rate"]] for a, r in res.items()])
        R.write_csv(os.path.join(out_dir, "page_faults_vs_frames.csv"), ["frames"] + list(curve),
                    [[f + 1] + [curve[a][f] for a in curve] for f in range(len(curve["FIFO"]))])
        R.chart_pages(curve, os.path.join(out_dir, "page_faults_vs_frames.png"))
    return res, R.render_pages(res, refs, frames, curve, anomalies, show_trace)


def run_alloc(cfg, out_dir=None):
    m = section(cfg, "memory")
    res = memory.compare_alloc(m.get("partitions"), m.get("requests"))
    log.info("allocation run done")
    if out_dir:
        R.chart_alloc(res, os.path.join(out_dir, "allocation_fragmentation.png"))
        R.write_csv(os.path.join(out_dir, "allocation_summary.csv"),
                    ["strategy", "placed", "failed", "internal_frag", "external_frag", "util_pct"],
                    [[s, len(r["placed"]), len(r["failed"]), r["internal_frag"], r["external_frag"], r["utilization"]]
                     for s, r in res.items()])
    return res, R.render_alloc(res, m.get("partitions"))


def run_banker(cfg):
    d = section(cfg, "deadlock")
    s = deadlock.safety(d.get("available"), d.get("max"), d.get("allocation"))
    req, txt = None, ""
    if isinstance(d.get("request"), dict):
        r = d["request"]
        req = deadlock.request_resources(d["available"], d["max"], d["allocation"], r.get("pid"), r.get("vector"))
        txt = f"P{r.get('pid')} asks {r.get('vector')}"
    log.info("banker run: safe=%s request=%s", s["safe"], req and req["granted"])
    return {"safety": s, "request": req}, R.render_banker(s, req, txt)


def run_detection(cfg):
    d = section(cfg, "deadlock")
    det = d.get("detection")
    if not isinstance(det, dict):
        raise ValidationError("deadlock.detection section missing")
    res = deadlock.detect(det.get("available"), det.get("allocation"), det.get("request"))
    log.info("detection run: %s", res)
    return res, R.render_detection(res)


def run_disk(cfg, out_dir=None):
    s = section(cfg, "storage")
    res = storage.compare(s.get("requests"), s.get("head"), s.get("disk_size"), s.get("direction", "up"))
    log.info("disk run: best=%s", min(res, key=lambda a: res[a]["total_movement"]))
    if out_dir:
        R.write_csv(os.path.join(out_dir, "disk_summary.csv"), ["algorithm", "total_movement", "avg_seek"],
                    [[a, r["total_movement"], r["avg_seek"]] for a, r in res.items()])
        R.chart_disk(res, os.path.join(out_dir, "disk_head_movement.png"))
    return res, R.render_disk(res, s["head"], s["disk_size"])


def run_batch(cfg, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    parts, summary = [], {}
    for name, fn in [("scheduling", lambda: run_scheduling(cfg, out_dir)),
                     ("page_replacement", lambda: run_pages(cfg, out_dir)),
                     ("allocation", lambda: run_alloc(cfg, out_dir)),
                     ("banker", lambda: run_banker(cfg)),
                     ("detection", lambda: run_detection(cfg)),
                     ("disk", lambda: run_disk(cfg, out_dir))]:
        res, text = fn()
        parts.append(text)
        summary[name] = "ok"
    try:
        from . import bridge
        parts.append(R.render_sysinfo(bridge.sysinfo()))
    except Exception as e:  # host info is optional; never fail the batch over it
        log.warning("sysinfo skipped: %s", e)
        parts.append(f"\n(host info unavailable: {e})")
    report = "\n".join(parts) + "\n"
    with open(os.path.join(out_dir, "trace.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    log.info("batch complete -> %s", out_dir)
    return report
