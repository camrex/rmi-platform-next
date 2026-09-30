#!/usr/bin/env python3
"""The rebuild's runner: one scheduled run takes a few tasks from PLAN.md and gives each to Pi.

    python3 runner/run.py            # what the nightly timer runs
    python3 runner/run.py --dry-run  # say what the next task is and stop

Per run: refresh the read-only source clones, pull this repo, then up to MAX_TASKS times take
the first unticked task in PLAN.md that is not behind an unapproved CHECKPOINT, run Pi on it
with the model its tier names, push the result. It stops early, and waits for the next run,
when a tier is unavailable (its fleet box is busy), the router refuses (budget spent), a task
fails, or the wall-clock budget for the night is used up. It never retries a failure in the
same run, and it marks a task blocked after MAX_ATTEMPTS failed runs.

Standard library only. Everything it does is logged to ~/logs/, and summarized in JOURNAL.md
when a task ends without the agent doing so.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
WORK = HOME / "work" / "rmi-platform-next"
SOURCES = HOME / "sources"
LOGS = HOME / "logs"
STATE = HOME / ".local" / "state" / "rebuild-runner.json"
SOURCE_REPOS = ["rmi-platform", "rmi-sbis-extract", "rmigis-agp-toolbox", "rmigis-pyt", "rmi-imagery-tiling"]
REMOTE = "git@github-platform-next:camrex/rmi-platform-next.git"

TIERS = {
    "drudge": "fleet-drudge",
    "coder": "fleet-coder",
    "light": "cloud-light",
    "standard": "cloud-standard",
    "heavy": "cloud-heavy",
}
MAX_TASKS = 3                 # per run
TASK_TIMEOUT_S = 2 * 3600     # one task
RUN_BUDGET_S = 4 * 3600 + 1800  # the whole night: 01:30 start, done by 06:00
MAX_ATTEMPTS = 3              # failed runs before a task is marked blocked

TASK_RE = re.compile(r"^- \[( |x)\] (\S+) \[(\w+)\] (.+)$")
CHECKPOINT_RE = re.compile(r"^## CHECKPOINT (\S+)")
UNAVAILABLE = re.compile(r"invalid model name|no deployments available|no healthy deployments", re.I)
BUDGET = re.compile(r"budget.{0,40}exceeded|exceeded.{0,40}budget|max_budget", re.I)


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def sh(*cmd, cwd=None, check=True, timeout=600, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, timeout=timeout, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


class Log:
    def __init__(self):
        LOGS.mkdir(parents=True, exist_ok=True)
        self.path = LOGS / f"run-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        self.f = open(self.path, "a")

    def __call__(self, msg: str) -> None:
        line = f"{dt.datetime.now().strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()


# ---- plan parsing, pure ------------------------------------------------------------------

def next_task(plan: str, approvals: set[str]):
    """The first unticked task not behind an unapproved checkpoint, or a reason there is none."""
    for line in plan.splitlines():
        cp = CHECKPOINT_RE.match(line.strip())
        if cp and cp.group(1) not in approvals:
            return None, f"waiting at checkpoint '{cp.group(1)}' (approvals/{cp.group(1)}.md missing)"
        m = TASK_RE.match(line.strip())
        if m and m.group(1) == " ":
            tid, tier, what = m.group(2), m.group(3), m.group(4)
            if tier not in TIERS:
                return None, f"task {tid} has unknown tier '{tier}'"
            return {"id": tid, "tier": tier, "what": what, "line": line.strip()}, None
    return None, "no unticked tasks"


def is_ticked(plan: str, tid: str) -> bool:
    return any((m := TASK_RE.match(l.strip())) and m.group(2) == tid and m.group(1) == "x"
               for l in plan.splitlines())


def mark_blocked(plan: str, tid: str, why: str) -> str:
    out = []
    for l in plan.splitlines():
        m = TASK_RE.match(l.strip())
        if m and m.group(2) == tid and m.group(1) == " ":
            l = f"- [x] {tid} [{m.group(3)}] BLOCKED ({why}): {m.group(4)}"
        out.append(l)
    return "\n".join(out) + "\n"


# ---- the edges ---------------------------------------------------------------------------

def refresh_sources(log: Log) -> None:
    SOURCES.mkdir(exist_ok=True)
    for r in SOURCE_REPOS:
        d = SOURCES / r
        try:
            if (d / ".git").exists():
                sh("chmod", "-R", "u+w", str(d))
                sh("git", "-C", str(d), "fetch", "-q", "--depth", "1", "origin")
                sh("git", "-C", str(d), "reset", "-q", "--hard", "FETCH_HEAD")
            else:
                sh("git", "clone", "-q", "--depth", "1", f"https://github.com/camrex/{r}", str(d), timeout=1200)
            head = sh("git", "-C", str(d), "rev-parse", "--short", "HEAD").stdout.strip()
            log(f"source {r} at {head}")
        except subprocess.CalledProcessError as e:
            log(f"source {r} could not be refreshed: {e.stdout.strip()[-200:]}")
        finally:
            if d.exists():
                sh("chmod", "-R", "a-w", str(d), check=False)  # read-only to the agent


def sync_work(log: Log) -> None:
    if not (WORK / ".git").exists():
        WORK.parent.mkdir(parents=True, exist_ok=True)
        sh("git", "clone", "-q", REMOTE, str(WORK))
    sh("git", "-C", str(WORK), "pull", "-q", "--rebase", "origin", "main")
    log(f"work at {sh('git', '-C', str(WORK), 'rev-parse', '--short', 'HEAD').stdout.strip()}")


def approvals() -> set[str]:
    d = WORK / "approvals"
    return {p.stem for p in d.glob("*.md") if p.name != "README.md"} if d.exists() else set()


def journal(entry: str) -> None:
    with open(WORK / "JOURNAL.md", "a") as f:
        f.write("\n" + entry.rstrip() + "\n")


def commit_and_push(msg: str, log: Log) -> None:
    sh("git", "-C", str(WORK), "add", "-A")
    if sh("git", "-C", str(WORK), "status", "--porcelain").stdout.strip():
        sh("git", "-C", str(WORK), "commit", "-q", "-m", msg)
    sh("git", "-C", str(WORK), "pull", "-q", "--rebase", "origin", "main")
    sh("git", "-C", str(WORK), "push", "-q", "origin", "HEAD:main")
    log(f"pushed {sh('git', '-C', str(WORK), 'rev-parse', '--short', 'HEAD').stdout.strip()}")


def run_pi(task: dict, log: Log, timeout_s: int) -> tuple[int, str]:
    model = TIERS[task["tier"]]
    prompt = (
        f"You are the unattended rmi-platform rebuild. Your task this run is {task['id']}:\n\n"
        f"{task['what']}\n\n"
        "Read MISSION.md and AGENTS.md first and follow them exactly: this task only, the "
        "source repositories are in ~/sources (read-only), journal what you did in JOURNAL.md, "
        "tick the task in PLAN.md if it is done, and commit. Do not push; the runner pushes."
    )
    env = dict(os.environ, PATH=f"{HOME}/.local/node/bin:{os.environ.get('PATH', '')}",
               PI_OFFLINE="1", PI_TELEMETRY="0")
    log(f"task {task['id']} [{task['tier']} -> {model}] starting")
    try:
        p = subprocess.run(["pi", "-p", "--provider", "rmi-router", "--model", model, prompt],
                           cwd=WORK, env=env, text=True, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout_s)
        out = p.stdout
        log(out[-4000:])
        return p.returncode, out
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        log(f"task {task['id']} timed out after {timeout_s}s")
        return 124, out


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {"attempts": {}}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-tasks", type=int, default=MAX_TASKS)
    a = ap.parse_args()

    lock = open(HOME / ".rebuild-runner.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another run is in progress")
        return 0

    log = Log()
    started = time.monotonic()
    sync_work(log)
    if not a.dry_run:
        refresh_sources(log)
    state = load_state()

    for _ in range(a.max_tasks):
        plan = (WORK / "PLAN.md").read_text()
        task, why = next_task(plan, approvals())
        if not task:
            log(why)
            if why.startswith("waiting") and not a.dry_run:
                last = (WORK / "JOURNAL.md").read_text().rstrip().splitlines()[-1:]
                if not last or "waiting at checkpoint" not in last[0]:
                    journal(f"## {utc()} runner — waiting\n\nRunner: {why}.")
                    commit_and_push("runner: waiting at checkpoint", log)
            return 0
        if a.dry_run:
            log(f"next: {task['id']} [{task['tier']} -> {TIERS[task['tier']]}] {task['what']}")
            return 0

        left = RUN_BUDGET_S - (time.monotonic() - started)
        if left < 600:
            log("night's time budget used up")
            break
        code, out = run_pi(task, log, int(min(TASK_TIMEOUT_S, left)))
        plan_after = (WORK / "PLAN.md").read_text()
        tail = "\n".join(out.strip().splitlines()[-6:])

        if code == 0 and is_ticked(plan_after, task["id"]):
            state["attempts"].pop(task["id"], None)
            save_state(state)
            commit_and_push(f"{task['id']}: {task['what'][:60]}", log)
            continue

        # Not done. Say why, keep any partial work, and stop for tonight.
        if UNAVAILABLE.search(out):
            reason = f"tier '{task['tier']}' unavailable (its fleet box is busy or offline); waiting"
        elif BUDGET.search(out):
            reason = "the router refused: cloud budget spent for this period; waiting for the reset"
        else:
            n = state["attempts"].get(task["id"], 0) + 1
            state["attempts"][task["id"]] = n
            reason = f"ended without finishing (exit {code}), attempt {n} of {MAX_ATTEMPTS}"
            if n >= MAX_ATTEMPTS:
                (WORK / "PLAN.md").write_text(mark_blocked(plan_after, task["id"], f"{n} failed runs"))
                reason += "; marked BLOCKED for the operator"
        save_state(state)
        journal(f"## {utc()} {task['id']} — runner\n\nRunner: {reason}.\n\n```\n{tail}\n```")
        commit_and_push(f"{task['id']}: runner note ({reason[:50]})", log)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
