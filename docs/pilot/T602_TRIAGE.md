# UAT defect triage

1. Reproduce and attach a trace ID.
2. Classify Blocker, Major, Minor, or Proposal.
3. Assign an owner and affected gate.
4. Fix on a focused branch and add regression coverage.
5. Redeploy staging and run isolation, E2E, and privacy canary checks.
6. QA verifies and records the result in `UAT_DEFECT_LOG.md`.

Privacy leaks, cross-owner visibility, missing citations, failed deletion, and
broken upload-to-question flow are always Blocker and stop pilot release.
