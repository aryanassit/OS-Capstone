import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from osim import bridge, runner, validation as V
from osim.errors import BridgeError, ValidationError
from osim.modules import deadlock, memory, scheduler, storage

P4 = [{"pid": "P1", "arrival": 0, "burst": 8}, {"pid": "P2", "arrival": 1, "burst": 4},
      {"pid": "P3", "arrival": 2, "burst": 9}, {"pid": "P4", "arrival": 3, "burst": 5}]
P3 = [{"pid": "P1", "arrival": 0, "burst": 24}, {"pid": "P2", "arrival": 0, "burst": 3},
      {"pid": "P3", "arrival": 0, "burst": 3}]
REFS = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
MX = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
AL = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
DQ = [98, 183, 37, 122, 14, 124, 65, 67]


class TestScheduler(unittest.TestCase):
    def test_fcfs_textbook(self):
        self.assertEqual(scheduler.simulate(P3, "FCFS")["avg_waiting"], 17.0)

    def test_sjf_textbook(self):
        self.assertEqual(scheduler.simulate(P3, "SJF")["avg_waiting"], 3.0)
        self.assertEqual(scheduler.simulate(P4, "SJF")["avg_waiting"], 7.75)

    def test_srtf_textbook(self):
        self.assertEqual(scheduler.simulate(P4, "SRTF")["avg_waiting"], 6.5)

    def test_rr_textbook(self):
        self.assertEqual(scheduler.simulate(P3, "RR", 4)["avg_waiting"], 5.67)

    def test_idle_gap(self):
        r = scheduler.simulate([{"pid": "A", "arrival": 5, "burst": 2}], "FCFS")
        self.assertEqual(r["gantt"][0][0], "IDLE")
        self.assertLess(r["cpu_utilization"], 100)

    def test_single_process_boundary(self):
        r = scheduler.simulate([{"pid": "A", "arrival": 0, "burst": 1}], "RR", 1)
        self.assertEqual((r["avg_waiting"], r["cpu_utilization"]), (0, 100.0))

    def test_quantum_larger_than_burst_equals_fcfs(self):
        self.assertEqual(scheduler.simulate(P3, "RR", 999)["avg_waiting"], scheduler.simulate(P3, "FCFS")["avg_waiting"])

    def test_invariants_all_algorithms(self):
        for a, r in scheduler.compare_all(P4, 3).items():
            for x in r["rows"]:
                self.assertEqual(x["turnaround"], x["waiting"] + x["burst"], a)
                self.assertGreaterEqual(x["waiting"], 0, a)
            self.assertEqual(sum(e - s for p, s, e in r["gantt"] if p != "IDLE"), 26, a)

    def test_priority_order(self):
        pr = [{"pid": "A", "arrival": 0, "burst": 3, "priority": 5}, {"pid": "B", "arrival": 0, "burst": 3, "priority": 1}]
        self.assertEqual(scheduler.simulate(pr, "PRIORITY")["gantt"][0][0], "B")

    def test_invalid(self):
        bad = [[], [{"pid": "A", "arrival": 0, "burst": 0}], [{"pid": "A", "arrival": -1, "burst": 2}],
               [{"pid": "A", "arrival": 0, "burst": 2}, {"pid": "A", "arrival": 1, "burst": 2}],
               [{"pid": "", "arrival": 0, "burst": 2}], [{"pid": "A", "arrival": "x", "burst": 2}],
               [{"pid": "IDLE", "arrival": 0, "burst": 2}], "nope"]
        for b in bad:
            with self.assertRaises(ValidationError, msg=str(b)):
                scheduler.simulate(b, "FCFS")
        with self.assertRaises(ValidationError):
            scheduler.simulate(P3, "RR", 0)
        with self.assertRaises(ValidationError):
            scheduler.simulate(P3, "LOTTERY")


class TestMemory(unittest.TestCase):
    def test_textbook_faults(self):
        r = memory.compare_pages(REFS, 3)
        self.assertEqual((r["FIFO"]["faults"], r["LRU"]["faults"], r["OPT"]["faults"]), (15, 12, 9))

    def test_opt_is_lower_bound(self):
        for f in range(1, 8):
            c = memory.compare_pages(REFS, f)
            self.assertLessEqual(c["OPT"]["faults"], min(c["FIFO"]["faults"], c["LRU"]["faults"]))

    def test_belady(self):
        curve = memory.fault_curve([1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5], 5)
        self.assertEqual(curve["FIFO"][2:4], [9, 10])
        self.assertEqual(memory.belady_anomaly(curve), [(3, 9, 10)])

    def test_one_frame_every_change_faults(self):
        self.assertEqual(memory.page_replacement([1, 1, 2, 2, 1], 1, "LRU")["faults"], 3)

    def test_frames_ge_unique_pages(self):
        self.assertEqual(memory.page_replacement([1, 2, 3, 1, 2, 3], 3, "FIFO")["faults"], 3)

    def test_alloc_textbook(self):
        parts, reqs = [100, 500, 200, 300, 600], [{"pid": "A", "size": 212}, {"pid": "B", "size": 417},
                                                  {"pid": "C", "size": 112}, {"pid": "D", "size": 426}]
        ff = memory.allocate(parts, reqs, "first")
        self.assertEqual([p["partition"] for p in ff["placed"]], [1, 4, 2])
        self.assertEqual(ff["failed"], ["D"])
        bf = memory.allocate(parts, reqs, "best")
        self.assertEqual(bf["failed"], [])
        wf = memory.allocate(parts, reqs, "worst")
        self.assertEqual(wf["failed"], ["D"])

    def test_invalid(self):
        for args in [([], 3), ([1, -2], 3), ([1, 2], 0), ([1, 2], 101), (["a"], 2), ("123", 2)]:
            with self.assertRaises(ValidationError, msg=str(args)):
                memory.page_replacement(*args, "FIFO")
        with self.assertRaises(ValidationError):
            memory.page_replacement([1], 1, "MRU")
        with self.assertRaises(ValidationError):
            memory.allocate([100], [{"pid": "A", "size": 0}], "first")
        with self.assertRaises(ValidationError):
            memory.allocate([100], [{"pid": "A", "size": 5}, {"pid": "A", "size": 5}], "first")


class TestDeadlock(unittest.TestCase):
    def test_safe_sequence(self):
        self.assertEqual(deadlock.safety([3, 3, 2], MX, AL)["sequence"], ["P1", "P3", "P4", "P0", "P2"])

    def test_unsafe(self):
        al = [[0, 1, 0], [3, 0, 2], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
        self.assertFalse(deadlock.safety([0, 0, 0], MX, al)["safe"])

    def test_request_granted_denied(self):
        self.assertTrue(deadlock.request_resources([3, 3, 2], MX, AL, 1, [1, 0, 2])["granted"])
        self.assertFalse(deadlock.request_resources([3, 3, 2], MX, AL, 4, [3, 3, 0])["granted"])   # > available
        after = [[0, 1, 0], [3, 0, 2], [3, 0, 2], [2, 1, 1], [0, 0, 2]]   # state after P1's grant
        r = deadlock.request_resources([2, 3, 0], MX, after, 0, [0, 2, 0])  # textbook: leads to unsafe state
        self.assertFalse(r["granted"])
        self.assertIn("UNSAFE", r["reason"])
        r = deadlock.request_resources([3, 3, 2], MX, AL, 1, [9, 9, 9])                              # > need
        self.assertIn("maximum", r["reason"])

    def test_detection(self):
        al = [[0, 1, 0], [2, 0, 0], [3, 0, 3], [2, 1, 1], [0, 0, 2]]
        self.assertFalse(deadlock.detect([0, 0, 0], al, [[0, 0, 0], [2, 0, 2], [0, 0, 0], [1, 0, 0], [0, 0, 2]])["deadlocked"])
        d = deadlock.detect([0, 0, 0], al, [[0, 0, 0], [2, 0, 2], [0, 0, 1], [1, 0, 0], [0, 0, 2]])
        self.assertEqual(d["processes"], ["P1", "P2", "P3", "P4"])

    def test_invalid(self):
        with self.assertRaises(ValidationError):
            deadlock.safety([3, 3], MX, AL)                      # column mismatch
        with self.assertRaises(ValidationError):
            deadlock.safety([3, 3, 2], MX, [[9, 9, 9]] * 5)      # allocation > max
        with self.assertRaises(ValidationError):
            deadlock.safety([3, 3, 2], MX, AL[:3])               # row mismatch
        with self.assertRaises(ValidationError):
            deadlock.request_resources([3, 3, 2], MX, AL, 9, [1, 0, 0])   # bad pid
        with self.assertRaises(ValidationError):
            deadlock.request_resources([3, 3, 2], MX, AL, 1, [1, 0])      # bad vector


class TestStorage(unittest.TestCase):
    def test_textbook_totals(self):
        r = storage.compare(DQ, 53, 200)
        got = {a: v["total_movement"] for a, v in r.items()}
        self.assertEqual(got, {"FCFS": 640, "SSTF": 236, "SCAN": 331, "CSCAN": 382, "LOOK": 299, "CLOOK": 322})

    def test_scan_down(self):
        self.assertEqual(storage.run("SCAN", DQ, 53, 200, "down")["total_movement"], 236)

    def test_all_requests_served(self):
        for a, r in storage.compare(DQ, 53, 200).items():
            self.assertEqual(sorted(r["order"]), sorted(DQ), a)

    def test_boundaries(self):
        self.assertEqual(storage.run("FCFS", [0], 0, 2)["total_movement"], 0)
        self.assertEqual(storage.run("SCAN", [199], 199, 200)["total_movement"], 0)
        self.assertEqual(storage.run("CSCAN", [5], 5, 200)["total_movement"], 194)  # head at 5 -> end only

    def test_invalid(self):
        for args in [([], 5, 100), ([100], 5, 100), ([-1], 5, 100), ([1], 100, 100), ([1], 5, 1), ([1], 5, "abc")]:
            with self.assertRaises(ValidationError, msg=str(args)):
                storage.run("FCFS", *args)
        with self.assertRaises(ValidationError):
            storage.run("ELEVATOR", [1], 5, 100)
        with self.assertRaises(ValidationError):
            storage.run("SCAN", [1], 5, 100, "sideways")


class TestRunnerAndBridge(unittest.TestCase):
    def test_missing_file_and_bad_json(self):
        with self.assertRaises(ValidationError):
            runner.load_config("/no/such/file.json")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{not json")
        with self.assertRaises(ValidationError):
            runner.load_config(f.name)
        os.unlink(f.name)

    def test_missing_section(self):
        with self.assertRaises(ValidationError):
            runner.run_disk({})

    def test_batch_writes_files(self):
        with tempfile.TemporaryDirectory() as d:
            runner.run_batch(runner.load_config(os.path.join(ROOT, "data", "sample_input.json")), d)
            for f in ("trace.txt", "scheduling_summary.csv", "disk_summary.csv"):
                self.assertTrue(os.path.isfile(os.path.join(d, f)), f)

    def test_stress_dataset_runs(self):
        cfg = runner.load_config(os.path.join(ROOT, "data", "stress_input.json"))
        res, _ = runner.run_scheduling(cfg)
        self.assertEqual(len(res), 5)

    def test_sysinfo_bridge(self):
        info = bridge.sysinfo()
        self.assertGreaterEqual(info["cpu_cores"], 1)
        self.assertIn("disk_use_pct", info)

    def test_live_processes_bridge(self):
        procs = bridge.live_processes(3)
        self.assertEqual(len(V.processes(procs)), len(procs))

    def test_bridge_rejects_bad_args_and_missing_script(self):
        with self.assertRaises(BridgeError):
            bridge.run_script("live_processes.sh", "abc")
        with self.assertRaises(BridgeError):
            bridge.run_script("nope.sh")

    def test_cli_exit_codes(self):
        run = lambda *a: subprocess.run([sys.executable, os.path.join(ROOT, "main.py"), *a], capture_output=True, text=True)
        self.assertEqual(run("disk").returncode, 0)
        r = run("disk", "--input", "/missing.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("ERROR", r.stderr)

    def test_menu_survives_bad_input(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "main.py")], input="x\n1\n3\nP1 0 0\n\n2\n0\n",
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Invalid choice", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
