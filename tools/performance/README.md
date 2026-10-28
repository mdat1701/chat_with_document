# Pilot performance smoke tests

Run the k6 scenarios against a staging deployment:

```powershell
k6 run -e BASE_URL=https://staging.example -e COOKIE="$env:COOKIE" `
  -e CSRF_TOKEN="$env:CSRF_TOKEN" k6/qa_load.js
k6 run -e BASE_URL=https://staging.example -e COOKIE="$env:COOKIE" `
  -e CSRF_TOKEN="$env:CSRF_TOKEN" -e PDF_PATH=fixtures/sample.pdf k6/ingestion_burst.js
```

Attach the JSON summary, deployment replica counts, TEI/LLM model IDs, and
the cleanup confirmation to the G-06 evidence record. The scripts do not
declare a pass without a real staging run.
