---
type: Decision
name: D26 Encrypted disaster-recovery backups may hold customer PII in the secondary
  region
id: D26
title: Encrypted disaster-recovery backups may hold customer PII in the secondary
  region
date: '2026-08-04'
DECIDED_IN:
- '[[Meeting/Security Review 2026-08-04]]'
MADE_BY:
- '[[Person/Sofia Marini]]'
OWNED_BY:
- '[[Person/Sofia Marini]]'
AFFECTS:
- '[[Project/Flux]]'
CONSTRAINS:
- target: '[[Technology/Orbit Cloud]]'
  stance: allows
  scope: dr-backups
DEPENDS_ON:
- '[[Decision/D10 Customer PII must stay in the primary cloud region]]'
---
# D26: Encrypted disaster-recovery backups may hold customer PII in the secondary region

Disaster recovery exception, backups only.
