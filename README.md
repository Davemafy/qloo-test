# Qloo API Probe Harness

A deliberately quota-conservative test harness for the Qloo hackathon API.

## Safety model

- The initial bootstrap commit triggers exactly one smoke-test job, guarded by an exact commit message.
- Ordinary pushes skip the job. Manual runs are available from GitHub Actions.
- The workflow accepts only `smoke` mode and a request ceiling of `1`.
- The script performs one fixed `GET /search` request. It has no retries, no loops and no fallback hosts.
- The API key is read only from the `QLOO_API_KEY` GitHub Actions secret. Never put it in source, artifacts, logs or chat.
- Redirects are blocked to prevent forwarding the API key to another host.
- Response bodies are bounded, sanitized and uploaded as a short-lived artifact (3 days).

## Inspect the smoke test

1. Open the repository's **Actions** tab.
2. Open the **Qloo probe** run triggered by the bootstrap commit.
3. Download the `qloo-probe-results` artifact.
4. Inspect `results.json`. It records the HTTP status, response shape and a bounded sanitized response.

If the initial run has not appeared, open **Actions → Qloo probe → Run workflow**, leaving `mode=smoke` and `max_requests=1`. Do not rerun a failed request until its failure status and endpoint are understood.

## Endpoint

The harness uses `https://hackathon.api.qloo.com`, the hackathon API host referenced by the event documentation. It does not try alternate hosts automatically.

## Next phase

Do not add discovery probes until the smoke response has been inspected. The next experiment should be designed around the actual response schema and should use a fixed, reviewable request matrix with a strict cap.

## Important

This is a controlled research harness, not production code. A successful search response confirms basic access only; it does not validate the Insights endpoint or prove any cultural hypothesis.
