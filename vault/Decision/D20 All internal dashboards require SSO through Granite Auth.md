---
type: Decision
name: D20 All internal dashboards require SSO through Granite Auth
id: D20
title: All internal dashboards require SSO through Granite Auth
date: '2026-03-17'
DECIDED_IN:
- '[[Meeting/Security Review 2026-03-17]]'
MADE_BY:
- '[[Person/Sofia Marini]]'
OWNED_BY:
- '[[Person/Sofia Marini]]'
AFFECTS:
- '[[Project/Beacon]]'
- '[[Project/Flux]]'
CONSTRAINS:
- target: '[[Technology/Granite Auth]]'
  stance: requires
  scope: internal-dashboards
DEPENDS_ON:
- '[[Decision/D07 Ember authenticates users with Granite Auth]]'
---
# D20: All internal dashboards require SSO through Granite Auth

Audit finding on shared passwords.
