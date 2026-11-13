"""Renders REAL captured command output to PNG images (docs/terminal_*.png).
These are renders of text, not OS screenshots - replace/add your own screenshots before submission."""
import os, subprocess, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def sh(cmd, stdin=None):
    r = subprocess.run(cmd, shell=True, cwd=ROOT, input=stdin, capture_output=True, text=True)
    return f"$ {cmd}\n" + (r.stdout + r.stderr).rstrip()


def strip_menu(text):
    import re
    keep = [l for l in text.splitlines()
            if not re.match(r"^\s+[0-9]\) ", l) and not l.startswith("====") and "OSim - OS Resource" not in l]
    return "\n".join(keep)


def render(text, name, max_lines=48, width=104, menu=False):
    if menu:
        text = strip_menu(text)
    lines = []
    for l in text.splitlines():
        lines.append(l[:width])
    lines = lines[:max_lines]
    fig = plt.figure(figsize=(11, 0.2 * len(lines) + 0.5), facecolor="#1e1e1e")
    fig.text(0.01, 0.99, "\n".join(lines), va="top", ha="left", family="DejaVu Sans Mono",
             fontsize=8.5, color="#d4d4d4", linespacing=1.25)
    fig.savefig(os.path.join(ROOT, "docs", name), dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("wrote", name)


render(sh("python3 -m unittest discover -s tests -v 2>&1 | tail -n 46"), "terminal_1_tests.png", 48)
render(sh("python3 main.py", "1\n1\n0\n"), "terminal_2_menu_scheduling.png", 48, menu=True)
render(sh("python3 main.py", "4\n1\n0\n"), "terminal_3_menu_banker.png", 40, menu=True)
render(sh("python3 main.py", "x\n6\n3\n98 183 999\n53\n200\nup\n3\n3\nP1 0 0\n\n0\n"),
       "terminal_4_input_errors.png", 30, menu=True)
render(sh("python3 main.py disk --input /missing.json; echo exit_code=$?"), "terminal_5_cli_error.png", 10)
render(sh("python3 main.py sysinfo"), "terminal_6_bash_bridge.png", 20)
render(sh("python3 main.py disk --input data/sample_input.json"), "terminal_7_disk.png", 30)
