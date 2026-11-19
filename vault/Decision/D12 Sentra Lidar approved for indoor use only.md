---
type: Decision
name: D12 Sentra Lidar approved for indoor use only
id: D12
title: Sentra Lidar approved for indoor use only
date: '2025-09-16'
DECIDED_IN:
- '[[Meeting/Architecture Review 2025-09-16]]'
MADE_BY:
- '[[Person/Priya Raman]]'
OWNED_BY:
- '[[Person/Priya Raman]]'
AFFECTS:
- '[[Project/Atlas]]'
- '[[Project/Drift]]'
CONSTRAINS:
- target: '[[Technology/Sentra Lidar]]'
  stance: forbids
  scope: outdoor
DEPENDS_ON:
- '[[Decision/D03 Use Sentra Lidar for Atlas picker arm sensing]]'
---
# D12: Sentra Lidar approved for indoor use only

Sunlight washes out returns outdoors; outdoor trials failed.
