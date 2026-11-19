---
type: Decision
name: D17 Move telemetry from Pulse Telemetry to Orbit Cloud native metrics
id: D17
title: Move telemetry from Pulse Telemetry to Orbit Cloud native metrics
date: '2026-01-13'
DECIDED_IN:
- '[[Meeting/Architecture Review 2026-01-13]]'
MADE_BY:
- '[[Person/Priya Raman]]'
OWNED_BY:
- '[[Person/Priya Raman]]'
AFFECTS:
- '[[Project/Beacon]]'
- '[[Project/Drift]]'
CONSTRAINS:
- target: '[[Technology/Orbit Cloud]]'
  stance: requires
  scope: telemetry
- target: '[[Technology/Pulse Telemetry]]'
  stance: forbids
  scope: telemetry
SUPERSEDES:
- '[[Decision/D02 Standardize fleet telemetry on Pulse Telemetry]]'
DEPENDS_ON:
- '[[Decision/D01 Adopt Orbit Cloud as the primary cloud provider]]'
---
# D17: Move telemetry from Pulse Telemetry to Orbit Cloud native metrics

Drops a vendor and a bill; replaces the 2025 telemetry standard.
