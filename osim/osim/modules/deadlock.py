"""Deadlock handling: Banker's safety + resource-request algorithm, and deadlock detection."""
from .. import validation as V


def _need(mx, al):
    return [[mx[i][j] - al[i][j] for j in range(len(mx[0]))] for i in range(len(mx))]


def safety(available, maximum, allocation):
    avail, mx, al = V.banker(available, maximum, allocation)
    need = _need(mx, al)
    n, m = len(mx), len(avail)
    work, finish, seq, steps = list(avail), [False] * n, [], []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                steps.append({"pid": f"P{i}", "work_before": list(work)})
                work = [work[j] + al[i][j] for j in range(m)]
                finish[i] = True
                seq.append(f"P{i}")
                progress = True
    return {"safe": all(finish), "sequence": seq if all(finish) else [],
            "unfinished": [f"P{i}" for i in range(n) if not finish[i]],
            "need": need, "steps": steps, "available": avail}


def request_resources(available, maximum, allocation, pid, request):
    avail, mx, al = V.banker(available, maximum, allocation)
    i = V.to_int(pid, "process index", 0, len(mx) - 1)
    req = V.int_list(request, "request", 0, 10**6)
    if len(req) != len(avail):
        raise V.ValidationError(f"request needs {len(avail)} values")
    need = _need(mx, al)
    m = len(avail)
    if any(req[j] > need[i][j] for j in range(m)):
        return {"granted": False, "reason": f"P{i} exceeded its declared maximum claim"}
    if any(req[j] > avail[j] for j in range(m)):
        return {"granted": False, "reason": f"resources not available; P{i} must wait"}
    new_avail = [avail[j] - req[j] for j in range(m)]
    new_al = [row[:] for row in al]
    new_al[i] = [new_al[i][j] + req[j] for j in range(m)]
    s = safety(new_avail, mx, new_al)
    if s["safe"]:
        return {"granted": True, "reason": "state stays safe", "sequence": s["sequence"]}
    return {"granted": False, "reason": "granting would leave the system in an UNSAFE state"}


def detect(available, allocation, request):
    avail, al, rq = V.detection(available, allocation, request)
    n, m = len(al), len(avail)
    work = list(avail)
    finish = [all(x == 0 for x in al[i]) for i in range(n)]  # holds nothing -> cannot be in a cycle
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(rq[i][j] <= work[j] for j in range(m)):
                work = [work[j] + al[i][j] for j in range(m)]
                finish[i] = True
                progress = True
    dead = [f"P{i}" for i in range(n) if not finish[i]]
    return {"deadlocked": bool(dead), "processes": dead}
