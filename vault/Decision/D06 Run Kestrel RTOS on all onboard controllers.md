---
type: Decision
name: D06 Run Kestrel RTOS on all onboard controllers
id: D06
title: Run Kestrel RTOS on all onboard controllers
date: '2025-05-13'
DECIDED_IN:
- '[[Meeting/Architecture Review 2025-05-13]]'
MADE_BY:
- '[[Person/Priya Raman]]'
OWNED_BY:
- '[[Person/Priya Raman]]'
AFFECTS:
- '[[Project/Atlas]]'
- '[[Project/Drift]]'
- '[[Project/Cobalt]]'
CONSTRAINS:
- target: '[[Technology/Kestrel RTOS]]'
  stance: requires
  scope: all
---
# D06: Run Kestrel RTOS on all onboard controllers

Real-time guarantees and a single toolchain.
