"""Generates data/stress_input.json deterministically (seed 42). Run: python3 data/make_stress.py"""
import json, os, random
random.seed(42)
procs = [{"pid": f"P{i+1}", "arrival": random.randint(0, 30), "burst": random.randint(1, 20),
          "priority": random.randint(0, 9)} for i in range(15)]
refs, cur = [], 3
for _ in range(80):  # locality: mostly stay near current page
    cur = max(0, min(9, cur + random.choice([-1, 0, 0, 1, 1]))) if random.random() < 0.8 else random.randint(0, 9)
    refs.append(cur)
m, n = 4, 6
mx = [[random.randint(2, 8) for _ in range(m)] for _ in range(n)]
al = [[random.randint(0, v // 2) for v in row] for row in mx]
data = {
    "scheduling": {"processes": procs, "quantum": 4},
    "memory": {"reference_string": refs, "frames": 4, "max_frames": 8,
               "partitions": [random.randint(50, 400) for _ in range(10)],
               "requests": [{"pid": f"M{i+1}", "size": random.randint(30, 350)} for i in range(10)]},
    "deadlock": {"available": [3, 2, 2, 3], "max": mx, "allocation": al,
                 "request": {"pid": 0, "vector": [1, 0, 0, 1]},
                 "detection": {"available": [0, 0, 0, 0], "allocation": al,
                               "request": [[random.choice([0, 0, 1, 2]) for _ in range(m)] for _ in range(n)]}},
    "storage": {"requests": [random.randint(0, 499) for _ in range(30)], "head": 250,
                "disk_size": 500, "direction": "up"},
}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stress_input.json")
json.dump(data, open(out, "w"), indent=2)
print("wrote", out)

# Belady dataset: classic reference string that makes FIFO fault MORE with 4 frames than with 3
import copy
sample = json.load(open(os.path.join(os.path.dirname(out), "sample_input.json")))
b = copy.deepcopy(sample)
b["memory"]["reference_string"] = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
b["memory"]["frames"] = 3
b["memory"]["max_frames"] = 6
json.dump(b, open(os.path.join(os.path.dirname(out), "belady_input.json"), "w"), indent=2)
print("wrote belady_input.json")
