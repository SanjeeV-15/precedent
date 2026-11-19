---
type: Decision
name: D18 Beacon fleet scheduling runs on Q-DB queues
id: D18
title: Beacon fleet scheduling runs on Q-DB queues
date: '2026-02-03'
DECIDED_IN:
- '[[Meeting/Beacon Planning 2026-02-03]]'
MADE_BY:
- '[[Person/Ben Hartley]]'
OWNED_BY:
- '[[Person/Ben Hartley]]'
AFFECTS:
- '[[Project/Beacon]]'
CONSTRAINS:
- target: '[[Technology/Quanta DB]]'
  stance: requires
  scope: beacon
DEPENDS_ON:
- '[[Decision/D08 Store fleet data in Quanta DB]]'
---
# D18: Beacon fleet scheduling runs on Q-DB queues

Avoids adding a message broker. Q-DB is our name for Quanta DB.
