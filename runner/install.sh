#!/usr/bin/env bash
# Install or refresh the runner's user units. Run as `rebuild` on rmi-nuc, from the work clone:
#     bash runner/install.sh
set -euo pipefail
cd "$(dirname "$0")/.."
install -d ~/.config/systemd/user
install -m 0644 runner/systemd/rebuild-run.service runner/systemd/rebuild-run.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now rebuild-run.timer
systemctl --user list-timers rebuild-run.timer --no-pager
