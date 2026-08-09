# Task Graph

```mermaid
flowchart TD
  A["Repository and provider readiness"] --> B["Source intake"]
  B --> C["Immutable source evidence"]
  C --> D["OCR and extraction"]
  D --> E["Validation and confidence"]
  E --> F["Duplicate and document grouping"]
  F --> G["Category and vendor suggestions"]
  G --> H{"Review required?"}
  H -->|Yes| I["Operator review"]
  H -->|No| J["Local bookkeeping record"]
  I --> J
  J --> K["Routing draft"]
  K --> L{"External capability and approval?"}
  L -->|No| M["Supervised or blocked handoff"]
  L -->|Yes| N["Idempotent external execution"]
  N --> O["Provider readback and attachment verification"]
  M --> P["Master ledger status"]
  O --> P
  P --> Q["Reconciliation"]
  Q --> R["Reports and compliance evidence"]
  R --> S["Verified recovery package"]
  O --> T{"Drive archive evidence complete?"}
  T -->|No| U["Keep source in place"]
  T -->|Yes| V["Archive source with audit evidence"]
  W["Persistent emergency stop"] -. blocks new steps .-> B
  W -. blocks new steps .-> D
  W -. blocks new steps .-> N
```

## Stabilization order

1. Repository/configuration/readiness.
2. Local critical path and invariant tests.
3. Operator review and safety controls.
4. Provider capability and approval boundaries.
5. Recovery, diagnostics, and audit evidence.
6. Live provider acceptance.
7. Deployment, security, privacy, and human acceptance sign-off.
