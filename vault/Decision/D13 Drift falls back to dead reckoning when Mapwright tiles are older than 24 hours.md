---
type: Decision
name: D13 Drift falls back to dead reckoning when Mapwright tiles are older than 24
  hours
id: D13
title: Drift falls back to dead reckoning when Mapwright tiles are older than 24 hours
date: '2025-10-07'
DECIDED_IN:
- '[[Meeting/Drift Sync 2025-10-07]]'
MADE_BY:
- '[[Person/Tomas Rivera]]'
OWNED_BY:
- '[[Person/Tomas Rivera]]'
AFFECTS:
- '[[Project/Drift]]'
CONSTRAINS:
- target: '[[Technology/Mapwright]]'
  stance: requires
  scope: drift
DEPENDS_ON:
- '[[Decision/D05 Drift uses Mapwright for map tiles]]'
---
# D13: Drift falls back to dead reckoning when Mapwright tiles are older than 24 hours

Avoids routing on stale maps.
