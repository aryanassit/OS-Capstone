"""Memory management: page replacement (FIFO/LRU/OPT) and fixed-partition allocation (first/best/worst fit)."""
from .. import validation as V


def _replace(refs, frames, algo):
    mem, trace, faults = [], [], 0
    last_used, loaded = {}, {}
    for i, page in enumerate(refs):
        victim, hit = None, page in mem
        if hit:
            pass
        else:
            faults += 1
            if len(mem) == frames:
                if algo == "FIFO":
                    victim = min(mem, key=lambda p: loaded[p])
                elif algo == "LRU":
                    victim = min(mem, key=lambda p: last_used[p])
                else:  # OPT: evict the page used farthest in the future (or never)
                    def nxt(p):
                        try:
                            return refs.index(p, i + 1)
                        except ValueError:
                            return float("inf")
                    victim = max(mem, key=nxt)
                mem[mem.index(victim)] = page
            else:
                mem.append(page)
            loaded[page] = i
        last_used[page] = i
        trace.append({"step": i + 1, "page": page, "frames": list(mem),
                      "fault": not hit, "evicted": victim})
    n = len(refs)
    return {"algo": algo, "faults": faults, "hits": n - faults, "trace": trace,
            "fault_rate": round(100 * faults / n, 2), "hit_ratio": round(100 * (n - faults) / n, 2)}


def page_replacement(refs, frames, algo):
    refs, frames = V.page_input(refs, frames)
    algo = algo.upper()
    if algo not in ("FIFO", "LRU", "OPT"):
        raise V.ValidationError("algorithm must be FIFO, LRU or OPT")
    return _replace(refs, frames, algo)


def compare_pages(refs, frames):
    return {a: page_replacement(refs, frames, a) for a in ("FIFO", "LRU", "OPT")}


def fault_curve(refs, max_frames):
    """Faults vs frame count per algorithm (reveals Belady's anomaly for FIFO)."""
    max_frames = V.to_int(max_frames, "max frames", 1, V.MAX_FRAMES)
    return {a: [page_replacement(refs, f, a)["faults"] for f in range(1, max_frames + 1)]
            for a in ("FIFO", "LRU", "OPT")}


def belady_anomaly(curve):
    f = curve["FIFO"]
    return [(i + 1, f[i], f[i + 1]) for i in range(len(f) - 1) if f[i + 1] > f[i]]


def allocate(partitions, requests, strategy):
    partitions, requests = V.partitions(partitions, requests)
    strategy = strategy.lower()
    if strategy not in ("first", "best", "worst"):
        raise V.ValidationError("strategy must be first, best or worst")
    used = [None] * len(partitions)
    placed, failed = [], []
    for r in requests:
        cands = [i for i, s in enumerate(partitions) if used[i] is None and s >= r["size"]]
        if not cands:
            failed.append(r["pid"])
            continue
        if strategy == "first":
            i = cands[0]
        elif strategy == "best":
            i = min(cands, key=lambda i: (partitions[i], i))
        else:
            i = max(cands, key=lambda i: (partitions[i], -i))
        used[i] = r
        placed.append({"pid": r["pid"], "size": r["size"], "partition": i,
                       "partition_size": partitions[i], "waste": partitions[i] - r["size"]})
    internal = sum(p["waste"] for p in placed)
    free_blocks = [s for i, s in enumerate(partitions) if used[i] is None]
    external = sum(free_blocks) if failed else 0  # free space that exists but could not serve a request
    total = sum(partitions)
    return {"strategy": strategy, "placed": placed, "failed": failed,
            "internal_frag": internal, "external_frag": external,
            "utilization": round(100 * sum(p["size"] for p in placed) / total, 2)}


def compare_alloc(partitions, requests):
    return {s: allocate(partitions, requests, s) for s in ("first", "best", "worst")}
