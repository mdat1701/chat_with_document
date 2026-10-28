# Quality tuning round 2

This log records one-change-at-a-time quality adjustments. Re-ingest the
approved corpus when changing chunk parameters, then compare the result with
`tools.evaluation.compare`.

| Change | Baseline | Candidate | Keep? | Reviewer |
|---|---:|---:|---|---|
| Pending staging evaluation | Pending | Pending | Pending | BA/PM |

Guardrails: `not_found_recall = 1.0`, `uncited_rate = 0`, and no regression in
the validation set. If guardrails cannot be met, hold the pilot and escalate.
