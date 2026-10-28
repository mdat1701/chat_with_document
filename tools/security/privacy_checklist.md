# G-04 privacy checklist

- [ ] TEI runs inside the trusted internal network.
- [ ] LLM receives only the question and at most eight retrieved chunks.
- [ ] Logs, spans, metrics, and analytics contain no document content.
- [ ] Cookies are HttpOnly, Secure, and SameSite=Lax.
- [ ] Object storage is private and owner-prefixed.
- [ ] Redis and PostgreSQL use TLS/ACL in staging and production.
- [ ] Canary scan returns zero findings.
- [ ] ATTT approval is attached to `docs/pilot/PILOT_GATE_EVIDENCE.md`.
