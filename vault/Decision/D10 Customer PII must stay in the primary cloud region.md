---
type: Decision
name: D10 Customer PII must stay in the primary cloud region
id: D10
title: Customer PII must stay in the primary cloud region
date: '2025-08-05'
DECIDED_IN:
- '[[Meeting/Security Review 2025-08-05]]'
MADE_BY:
- '[[Person/Sofia Marini]]'
OWNED_BY:
- '[[Person/Sofia Marini]]'
AFFECTS:
- '[[Project/Flux]]'
- '[[Project/Ember]]'
CONSTRAINS:
- target: '[[Technology/Orbit Cloud]]'
  stance: forbids
  scope: customer-pii-outside-primary
DEPENDS_ON:
- '[[Decision/D01 Adopt Orbit Cloud as the primary cloud provider]]'
---
# D10: Customer PII must stay in the primary cloud region

Data residency commitment in customer contracts.
