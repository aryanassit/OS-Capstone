"""Python <-> Bash integration: runs the helper scripts in bash/ and turns their output into Python data."""
import os
import shutil
import subprocess

from .errors import BridgeError
from .logger import get_logger

log = get_logger("bridge")
BASH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bash")


def run_script(name, *args, timeout=10):
    path = os.path.join(BASH_DIR, name)
    if shutil.which("bash") is None:
        raise BridgeError("bash is not installed")
    if not os.path.isfile(path):
        raise BridgeError(f"helper script not found: {name}")
    try:
        r = subprocess.run(["bash", path, *map(str, args)], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        log.error("script %s timed out", name)
        raise BridgeError(f"{name} timed out after {timeout}s")
    if r.returncode != 0:
        log.error("script %s failed (%s): %s", name, r.returncode, r.stderr.strip())
        raise BridgeError(f"{name} failed: {r.stderr.strip() or 'exit ' + str(r.returncode)}")
    log.info("script %s ok", name)
    return r.stdout


def sysinfo():
    out = {}
    for line in run_script("sysinfo.sh").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = int(v) if v.isdigit() else v
    return out


def live_processes(n=8):
    """Real PIDs/nice values from the host. Burst is a PROXY (RSS memory -> 1..15 time units); arrival is staggered."""
    rows = []
    for i, line in enumerate(run_script("live_processes.sh", n).splitlines()):
        parts = line.split(",", 3)
        if len(parts) != 4:
            continue
        pid, nice, rss, comm = parts
        rows.append({"pid": f"{comm[:8]}:{pid}", "arrival": i,
                     "burst": max(1, min(15, int(rss) // 20000)),
                     "priority": max(0, min(39, int(nice) + 20))})
    if not rows:
        raise BridgeError("no processes returned by host")
    return rows
