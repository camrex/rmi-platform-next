"""The runner's plan parsing. python3 -m unittest discover runner"""
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
