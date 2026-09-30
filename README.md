# rmi-platform-next

The unattended rebuild of rmi-platform. Nobody drives it: a scheduled runner on `rmi-nuc` takes
one task at a time from `PLAN.md`, gives it to a model through RMI's LLM router, and pushes the
result here.

| file | what |
|---|---|
| `MISSION.md` | what it is for; the operator's brief |
| `AGENTS.md` | how every run works; the rules |
| `PLAN.md` | the task list, with the model tier for each, and the checkpoints |
| `JOURNAL.md` | what each run did |
| `approvals/` | the operator's approvals; a checkpoint passes when its file exists |
| `docs/` | what the runs produce: inventories, reviews, the architecture proposal |
| `runner/` | the runner, its tests, and its systemd units |

## For the operator

- **Progress:** read `JOURNAL.md` and the commits.
- **Steer:** edit `PLAN.md` (add, reorder, delete tasks) or `MISSION.md`. The next run follows.
- **Approve the architecture:** read `docs/architecture/PROPOSAL.md`, then add
  `approvals/architecture.md` saying approved or what to change.
- **Pause:** `ssh rebuild@rmi-nuc 'systemctl --user disable --now rebuild-run.timer'`.
- **Run now:** `ssh rebuild@rmi-nuc 'systemctl --user start --no-block rebuild-run'`.

## How it is fenced

It runs as the unprivileged user `rebuild`, whose traffic can reach only the router and the
public internet (rmi-fleet `deploy/bootstrap-rebuild-host.sh`). It reads the source repos with
a read-only token and writes only here with a deploy key. Its router key has $50 a month of
cloud and cannot use the most expensive tier. See rmi-fleet
`decisions/2026-09-29-rebuild-host.md`.
