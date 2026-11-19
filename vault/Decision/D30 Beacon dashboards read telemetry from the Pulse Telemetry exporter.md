---
type: Decision
name: D30 Beacon dashboards read telemetry from the Pulse Telemetry exporter
id: D30
title: Beacon dashboards read telemetry from the Pulse Telemetry exporter
date: '2026-02-17'
DECIDED_IN:
- '[[Meeting/Beacon Planning 2026-02-17]]'
MADE_BY:
- '[[Person/Ben Hartley]]'
OWNED_BY:
- '[[Person/Ben Hartley]]'
AFFECTS:
- '[[Project/Beacon]]'
CONSTRAINS:
- target: '[[Technology/Pulse Telemetry]]'
  stance: requires
  scope: beacon
DEPENDS_ON:
- '[[Decision/D02 Standardize fleet telemetry on Pulse Telemetry]]'
---
# D30: Beacon dashboards read telemetry from the Pulse Telemetry exporter

Reuses the existing exporter.
