"""Input validation. Every public function returns clean data or raises ValidationError."""
from .errors import ValidationError

MAX_PROCS = 500
MAX_FRAMES = 100
MAX_REFS = 10_000
MAX_DISK_REQS = 1_000


def to_int(v, name, lo=None, hi=None):
    if isinstance(v, bool):
        raise ValidationError(f"{name} must be an integer, got {v!r}")
    try:
        if isinstance(v, float) and not v.is_integer():
            raise ValueError
        n = int(v)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer, got {v!r}")
    if lo is not None and n < lo:
        raise ValidationError(f"{name} must be >= {lo}, got {n}")
    if hi is not None and n > hi:
        raise ValidationError(f"{name} must be <= {hi}, got {n}")
    return n


def int_list(v, name, lo=None, hi=None, min_len=1, max_len=None):
    if not isinstance(v, (list, tuple)):
        raise ValidationError(f"{name} must be a list")
    if len(v) < min_len:
        raise ValidationError(f"{name} needs at least {min_len} value(s)")
    if max_len is not None and len(v) > max_len:
        raise ValidationError(f"{name} has too many values (max {max_len})")
    return [to_int(x, f"{name}[{i}]", lo, hi) for i, x in enumerate(v)]


def processes(raw):
    if not isinstance(raw, list) or not raw:
        raise ValidationError("process list must be a non-empty list")
    if len(raw) > MAX_PROCS:
        raise ValidationError(f"too many processes (max {MAX_PROCS})")
    seen, out = set(), []
    for i, p in enumerate(raw):
        if not isinstance(p, dict):
            raise ValidationError(f"process #{i + 1} must be an object")
        pid = str(p.get("pid", "")).strip()
        if not pid:
            raise ValidationError(f"process #{i + 1} has no pid")
        if pid == "IDLE":
            raise ValidationError("pid 'IDLE' is reserved")
        if pid in seen:
            raise ValidationError(f"duplicate pid {pid}")
        seen.add(pid)
        out.append({
            "pid": pid,
            "arrival": to_int(p.get("arrival"), f"{pid}.arrival", 0, 10**6),
            "burst": to_int(p.get("burst"), f"{pid}.burst", 1, 10**4),
            "priority": to_int(p.get("priority", 0), f"{pid}.priority", 0, 10**4),
        })
    return out


def quantum(q):
    return to_int(q, "time quantum", 1, 10**4)


def page_input(refs, frames):
    return (int_list(refs, "reference string", 0, 10**6, max_len=MAX_REFS),
            to_int(frames, "frames", 1, MAX_FRAMES))


def partitions(parts, procs):
    parts = int_list(parts, "partitions", 1, 10**7, max_len=MAX_PROCS)
    if not isinstance(procs, list) or not procs:
        raise ValidationError("memory requests must be a non-empty list")
    out, seen = [], set()
    for i, p in enumerate(procs):
        pid = str(p.get("pid", "")).strip() if isinstance(p, dict) else ""
        if not pid or pid in seen:
            raise ValidationError(f"memory request #{i + 1}: missing or duplicate pid")
        seen.add(pid)
        out.append({"pid": pid, "size": to_int(p.get("size"), f"{pid}.size", 1, 10**7)})
    return parts, out


def _matrix(m, name, rows=None, cols=None):
    if not isinstance(m, list) or not m:
        raise ValidationError(f"{name} must be a non-empty matrix")
    out = [int_list(r, f"{name}[{i}]", 0, 10**6) for i, r in enumerate(m)]
    width = cols if cols is not None else len(out[0])
    if any(len(r) != width for r in out):
        raise ValidationError(f"{name} rows must all have {width} columns")
    if rows is not None and len(out) != rows:
        raise ValidationError(f"{name} must have {rows} rows")
    return out


def banker(available, maximum, allocation):
    avail = int_list(available, "available", 0, 10**6)
    m = len(avail)
    mx = _matrix(maximum, "max", cols=m)
    al = _matrix(allocation, "allocation", rows=len(mx), cols=m)
    for i in range(len(mx)):
        for j in range(m):
            if al[i][j] > mx[i][j]:
                raise ValidationError(f"allocation[{i}][{j}]={al[i][j]} exceeds max[{i}][{j}]={mx[i][j]}")
    return avail, mx, al


def detection(available, allocation, request):
    avail = int_list(available, "available", 0, 10**6)
    al = _matrix(allocation, "allocation", cols=len(avail))
    rq = _matrix(request, "request", rows=len(al), cols=len(avail))
    return avail, al, rq


def disk(requests, head, disk_size, direction="up"):
    size = to_int(disk_size, "disk size", 2, 10**6)
    h = to_int(head, "head", 0, size - 1)
    reqs = int_list(requests, "disk requests", 0, size - 1, max_len=MAX_DISK_REQS)
    if direction not in ("up", "down"):
        raise ValidationError("direction must be 'up' or 'down'")
    return reqs, h, size, direction
