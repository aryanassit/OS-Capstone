"""Disk scheduling: FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK.

Convention: head movement is the sum of |position changes| along the head path.
SCAN/C-SCAN travel to the physical disk end; the C-SCAN/C-LOOK return jump IS counted.
"""
from .. import validation as V


def _result(name, head, path, served, size):
    moves = [abs(b - a) for a, b in zip([head] + path, path)]
    total = sum(moves)
    return {"algo": name, "path": [head] + path, "order": served, "total_movement": total,
            "avg_seek": round(total / len(served), 2)}


def run(algo, requests, head, disk_size, direction="up"):
    reqs, head, size, direction = V.disk(requests, head, disk_size, direction)
    algo = algo.upper()
    up = sorted(r for r in reqs if r >= head)
    down = sorted((r for r in reqs if r < head), reverse=True)
    end = size - 1
    if algo == "FCFS":
        path = served = list(reqs)
    elif algo == "SSTF":
        left, cur, served = list(reqs), head, []
        while left:
            nxt = min(left, key=lambda r: (abs(r - cur), r))
            left.remove(nxt)
            served.append(nxt)
            cur = nxt
        path = served
    elif algo in ("SCAN", "LOOK"):
        first, second = (up, down) if direction == "up" else (down, up)
        edge = end if direction == "up" else 0
        served = first + second
        if algo == "LOOK":
            path = first + second
        else:  # SCAN always runs to the physical edge before reversing
            path = first + ([edge] if first[-1:] != [edge] else []) + second
    elif algo in ("CSCAN", "CLOOK"):
        if direction == "up":
            first, wrap_from, wrap_to, second = up, end, 0, sorted(down)
        else:
            first, wrap_from, wrap_to, second = down, 0, end, sorted(up, reverse=True)
        served = first + second
        if algo == "CSCAN":  # run to the edge, then (only if work remains) jump to the other edge
            path = first + ([wrap_from] if first[-1:] != [wrap_from] else []) + ([wrap_to] + second if second else [])
        else:
            path = first + second  # jump goes straight from last request to first request of other side
    else:
        raise V.ValidationError("algorithm must be FCFS, SSTF, SCAN, CSCAN, LOOK or CLOOK")
    return _result(algo, head, list(path), list(served), size)


ALGOS = ("FCFS", "SSTF", "SCAN", "CSCAN", "LOOK", "CLOOK")


def compare(requests, head, disk_size, direction="up"):
    return {a: run(a, requests, head, disk_size, direction) for a in ALGOS}
