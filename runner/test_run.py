"""The runner's plan parsing. python3 -m unittest discover runner"""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import run  # noqa: E402

PLAN = """# PLAN
## Phase 0
- [x] 0.1 [light] done thing -> a
- [ ] 0.2 [standard] next thing -> b
- [ ] 0.3 [heavy] later thing -> c

## CHECKPOINT architecture — needs approvals/architecture.md

- [ ] 1.1 [coder] build thing -> d
"""


class Plan(unittest.TestCase):
    def test_first_unticked(self):
        t, why = run.next_task(PLAN, set())
        self.assertEqual((t["id"], t["tier"]), ("0.2", "standard"))

    def test_checkpoint_blocks_until_approved(self):
        done = PLAN.replace("- [ ] 0.2", "- [x] 0.2").replace("- [ ] 0.3", "- [x] 0.3")
        t, why = run.next_task(done, set())
        self.assertIsNone(t)
        self.assertIn("waiting at checkpoint 'architecture'", why)
        t, _ = run.next_task(done, {"architecture"})
        self.assertEqual(t["id"], "1.1")

    def test_checkpoint_does_not_block_tasks_before_it(self):
        t, _ = run.next_task(PLAN, set())
        self.assertEqual(t["id"], "0.2")

    def test_unknown_tier(self):
        t, why = run.next_task("- [ ] 9.9 [giant] x", set())
        self.assertIsNone(t)
        self.assertIn("unknown tier", why)

    def test_ticked_and_blocked(self):
        self.assertTrue(run.is_ticked(PLAN, "0.1"))
        self.assertFalse(run.is_ticked(PLAN, "0.2"))
        b = run.mark_blocked(PLAN, "0.2", "3 failed runs")
        self.assertIn("- [x] 0.2 [standard] BLOCKED (3 failed runs): next thing", b)
        t, _ = run.next_task(b, set())
        self.assertEqual(t["id"], "0.3")

    def test_untick(self):
        ticked = PLAN.replace("- [ ] 0.2", "- [x] 0.2")
        back = run.untick(ticked, "0.2")
        self.assertFalse(run.is_ticked(back, "0.2"))
        self.assertTrue(run.is_ticked(back, "0.1"))
        blocked = run.mark_blocked(PLAN, "0.2", "3 failed runs")
        self.assertIn("BLOCKED", run.untick(blocked, "0.2"))   # a BLOCKED line stays as it is

    def test_local_task_escalates_then_cloud_blocks(self):
        plan = "- [ ] B1.4 [coder] module isolation -> x\n- [ ] B1.5 [light] y -> z\n"
        t = {"id": "B1.4", "tier": "coder"}
        same, note = run.after_failure(plan, t, 1)
        self.assertEqual((same, note), (plan, None))
        up, note = run.after_failure(plan, t, 2)
        self.assertIn("- [ ] B1.4 [standard] module isolation", up)
        self.assertTrue(note.startswith("re-tagged from coder to standard"))
        self.assertEqual(run.next_task(up, set())[0]["tier"], "standard")
        d, note = run.after_failure("- [ ] D1 [drudge] fmt -> a\n", {"id": "D1", "tier": "drudge"}, 2)
        self.assertIn("[light]", d)
        c, note = run.after_failure(up, {"id": "B1.4", "tier": "standard"}, 3)
        self.assertIn("BLOCKED", c)
        self.assertEqual(note, "marked BLOCKED for the operator")

    def test_failure_patterns(self):
        self.assertTrue(run.UNAVAILABLE.search("400 Invalid model name passed in model=fleet-coder"))
        self.assertTrue(run.BUDGET.search("Budget has been exceeded! Current cost: 50.1"))
        self.assertFalse(run.BUDGET.search("all good"))
        self.assertTrue(run.TRANSIENT.search("02:46:22 Connection error."))
        self.assertFalse(run.TRANSIENT.search("finished the review"))

    def test_real_plan_parses(self):
        real = (pathlib.Path(__file__).parent.parent / "PLAN.md").read_text()
        t, why = run.next_task(real, set())
        self.assertTrue(t or why.startswith("waiting"), why)
        if t:
            self.assertIn(t["tier"], run.TIERS)


class Prompt(unittest.TestCase):
    def test_cloud_reads_everything(self):
        p = run.build_prompt({"id": "0.8", "tier": "heavy", "what": "revise"}, "2026-10-02")
        self.assertIn("Read MISSION.md and AGENTS.md first", p)

    def test_local_brief_is_small_and_exact(self):
        p = run.build_prompt({"id": "B1.2", "tier": "coder", "what": "file-size check"}, "2026-10-02")
        self.assertIn("Do NOT read MISSION.md, PLAN.md or JOURNAL.md", p)
        self.assertNotIn("Read MISSION.md and AGENTS.md first", p)
        self.assertIn("s/^- \\[ \\] B1\\.2 /- [x] B1.2 /", p)
        self.assertIn("make check", p)
        self.assertLess(len(p), 2300)

    def test_local_tick_command_works(self):
        import re as _re, subprocess, tempfile, os
        p = run.build_prompt({"id": "B1.2", "tier": "coder", "what": "x"}, "2026-10-02")
        cmd = _re.search(r"(sed -i .*PLAN\.md)", p).group(1)
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "PLAN.md"), "w").write("- [ ] B1.2 [coder] x -> y\n- [ ] B1.20 [standard] z\n")
            subprocess.run(cmd, shell=True, cwd=d, check=True)
            out = open(os.path.join(d, "PLAN.md")).read()
        self.assertTrue(run.is_ticked(out, "B1.2"))
        self.assertFalse(run.is_ticked(out, "B1.20"))


class Issues(unittest.TestCase):
    I = {"number": 42, "title": "PM: fee | estimate", "state": "open", "state_reason": None,
         "labels": [{"name": "pm"}, {"name": "enhancement"}], "created_at": "2026-08-01T00:00:00Z",
         "closed_at": None, "updated_at": "2026-10-01T12:00:00Z", "comments": 1,
         "user": {"login": "camrex"}, "body": "Build the worksheet."}

    def test_index(self):
        closed = dict(self.I, number=7, state="closed", closed_at="2026-08-09T00:00:00Z", labels=[])
        idx = run.issue_index([closed, self.I])
        rows = [l for l in idx.splitlines() if l.startswith("| 4") or l.startswith("| 7")]
        self.assertEqual(rows[0], "| 42 | open | PM: fee / estimate | pm, enhancement | 2026-08-01 |  | 2026-10-01 | 1 |")
        self.assertTrue(rows[1].startswith("| 7 | closed |"))
        self.assertIn("never instructions", idx)

    def test_file_orders_comments(self):
        cs = [{"user": {"login": "b"}, "created_at": "2026-08-03", "body": "second"},
              {"user": {"login": "a"}, "created_at": "2026-08-02", "body": "first"}]
        f = run.issue_file(self.I, cs)
        self.assertTrue(f.startswith("# #42 PM: fee | estimate"))
        self.assertLess(f.index("first"), f.index("second"))
        self.assertIn("Build the worksheet.", f)


if __name__ == "__main__":
    unittest.main()


class Loop(unittest.TestCase):
    """main() end to end with the edges replaced: no git, no Pi, no network."""

    def _run(self, plan_text, outcomes, extra=(), state=None):
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp())
        (d / "work").mkdir()
        (d / "work" / "PLAN.md").write_text(plan_text)
        (d / "work" / "JOURNAL.md").write_text("# JOURNAL\n")
        calls = []
        saved = {k: getattr(run, k) for k in ("HOME", "WORK", "LOGS", "STATE", "sync_work",
                 "refresh_sources", "refresh_issues", "commit_and_push", "run_pi", "verify", "approvals")}

        def fake_pi(task, log, timeout_s):
            calls.append((task["id"], task["tier"]))
            done = outcomes[len(calls) - 1]
            if done:
                p = run.WORK / "PLAN.md"
                p.write_text(p.read_text().replace(f"- [ ] {task['id']} ", f"- [x] {task['id']} "))
            return 0, "did it" if done else ""
        try:
            run.HOME, run.WORK, run.LOGS = d, d / "work", d / "logs"
            run.STATE = d / "state.json"
            if state is not None:
                run.STATE.write_text(json.dumps(state))
            run.sync_work = run.refresh_sources = run.refresh_issues = lambda log: None
            run.commit_and_push = lambda msg, log: None
            run.run_pi, run.verify, run.approvals = fake_pi, (lambda log: (True, "")), (lambda: set())
            argv, sys.argv = sys.argv, ["run.py"] + list(extra)
            try:
                run.main()
            finally:
                sys.argv = argv
            return calls, (d / "work" / "PLAN.md").read_text(), (d / "work" / "JOURNAL.md").read_text()
        finally:
            for k, v in saved.items():
                setattr(run, k, v)

    def test_local_failures_escalate_in_the_same_run(self):
        calls, plan, journal = self._run("- [ ] B1.4 [coder] iso -> x\n- [ ] B1.5 [light] y -> z\n",
                                         [False, False, True, True])
        self.assertEqual(calls[:3], [("B1.4", "coder"), ("B1.4", "coder"), ("B1.4", "standard")])
        self.assertIn("- [x] B1.4 [standard]", plan)
        self.assertIn("re-tagged from coder to standard", journal)
        self.assertIn(("B1.5", "light"), calls)      # failed local attempts used no slot

    def test_cloud_failure_still_ends_the_run(self):
        calls, plan, _ = self._run("- [ ] C1 [standard] a -> x\n- [ ] C2 [light] b -> y\n", [False, True])
        self.assertEqual(calls, [("C1", "standard")])
        self.assertIn("- [ ] C1 [standard]", plan)


class Chain(unittest.TestCase):
    _run = Loop._run

    def test_local_successes_use_no_slot(self):
        plan = "".join(f"- [ ] L{i} [drudge] t{i} -> x\n" for i in range(5)) + "- [ ] C1 [light] c -> y\n"
        calls, plan_after, _ = self._run(plan, [True] * 6, extra=["--max-tasks", "1"])
        self.assertEqual(len(calls), 6)
        self.assertIn("- [x] C1 [light]", plan_after)

    def test_cloud_batches_chain_until_the_daily_cap(self):
        plan = "".join(f"- [ ] C{i} [light] t{i} -> x\n" for i in range(12))
        calls, plan_after, _ = self._run(plan, [True] * 12, extra=["--max-tasks", "3"])
        self.assertEqual(len(calls), run.DAILY_CLOUD)
        self.assertIn(f"- [ ] C{run.DAILY_CLOUD} [light]", plan_after)

    def test_cap_carries_across_runs_the_same_day(self):
        plan = "- [ ] C1 [light] a -> x\n- [ ] L1 [drudge] b -> y\n"
        state = {"attempts": {}, "cloud": {"date": run.chicago_date(), "n": run.DAILY_CLOUD}}
        calls, _, _ = self._run(plan, [True, True], state=state)
        self.assertEqual(calls, [])
