# ATED 0.5 architecture

```text
Historian (schema 2) ───────────────┐
Device Registry (schema 1) ────────┼─> Decision / Explain facts
Event Journal (schema 1) ──────────┘             │
                                                 v
                                      Presentation Engine
                                      levels 0–4 / UI profile
```

Explain facts must remain canonical and complete. Presentation Engine may reveal less detail but must never rewrite decision evidence, confidence, blockers, alternatives, or actor provenance. Adaptive personalization is intentionally deferred; alpha.1 uses explicit deterministic levels only.
