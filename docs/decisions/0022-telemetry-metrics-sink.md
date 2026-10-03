---
status: ruled
kind: architecture
date: 2026-08-06
refs: []
source_status: "Accepted (2026-08-06) · **Shipped**: end to end in v1.19.0 ·"
imported_from: rmi-platform/docs/adr/0022-telemetry-metrics-sink.md
imported_on: 2026-10-03
---
# 0022 — Telemetry: Prometheus-style metrics, Grafana Cloud sink

**Status**: Accepted (2026-08-06) · **Shipped**: end to end in v1.19.0 ·
**Resolves**: #11 · **Informed by**: owner decision 2026-08-06
(Prometheus/Grafana preferred; Grafana Cloud free tier chosen over
self-hosting).

## Context

The platform emits structured JSON logs to stdout, captured by Lightsail's log
viewer, with a CloudWatch alarm → SNS email for infra-level signals. There are
no application metrics: no request latency/error rates, no worker-job
visibility. Two Lightsail facts shape the options:

- Lightsail container services **cannot ship logs to CloudWatch Logs**, so the
  "CloudWatch agent" and EMF-over-logs paths in #11's original option list do
  not exist here. CloudWatch is reachable only via `put_metric_data` — coarse,
  per-metric billing, no real histograms.
- Prometheus is pull-based and the worker container has no public HTTP
  surface; but a Lightsail container-service deployment may run **multiple
  containers**, which can reach each other over localhost.

AWS documents self-hosting Prometheus on a Lightsail *instance*
([guide](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-install-prometheus.html)).
Reviewed and rejected as the primary path: it is a hand-built pet server
(vim-edited configs, systemd units), its tutorial posture opens ports
9090/9100 to the world **unauthenticated over plain HTTP**, it excludes
Grafana, and it adds an OS to patch — disproportionate ops burden for a
three-person org.

## Decision

1. **Instrumentation is vendor-neutral and code-owned**: `prometheus_client`
   in-process — golden signals first (request count/latency/error class by
   route *template*, bounded cardinality), worker-job metrics next. The
   `/metrics` exposition is bearer-token guarded and **disabled until
   `RMI_METRICS_TOKEN` is set** (404, not 401, when unconfigured). Wired at
   the composition root so modules need zero per-module work.
2. **The sink is Grafana Cloud (free tier)**: a **Grafana Alloy** container
   rides in the Lightsail deployment beside `api` and `worker`, scrapes them
   over localhost with the token, and `remote_write`s to Grafana Cloud's
   hosted Prometheus. Dashboards and golden-signal alert rules live in
   Grafana Cloud; alerts email the team.
3. **SNS stays** for the infra-level alarms Lightsail raises natively (DB
   disk/CPU); Grafana owns application-level alerting. One alarm channel per
   layer, no duplication.
4. **Slices**: (1) instrumentation + guarded `/metrics` on the api — this
   ADR's PR; (2) worker metrics port + Alloy sidecar + Grafana Cloud account
   wiring + baseline dashboard/alerts — needs owner account creation, tracked
   on #11.

## Consequences

- The metrics grammar (`rmi_http_*`, worker metrics to follow) outlives the
  sink choice: self-hosting later means pointing a different scraper at the
  same endpoints, not re-instrumenting.
- Free-tier bounds (10k series, 14-day retention) are the accepted trade;
  bounded label cardinality is a design rule, not an optimization. If limits
  pinch or data-residency needs arise, the documented fallback is a
  containerized (not tutorial-style) self-hosted stack on a small instance —
  with TLS and auth, which the AWS guide omits.
- The scrape token is a shared secret between the deployment's containers and
  never grants anything but exposition reads.
- Rejected: CloudWatch custom metrics (no histograms, per-metric pricing, and
  the agent path doesn't exist on Lightsail containers); the tutorial-style
  self-hosted instance (posture above); logging pipelines (out of scope — the
  Lightsail log viewer remains the log surface for now).
