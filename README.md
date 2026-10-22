# Qloo API Probe Harness

A deliberately quota-conservative harness for validating one cross-domain Qloo Insights request.

## Safety model

- The probe requires `QLOO_API_KEY` and `MAX_REQUESTS=1`; otherwise it exits before making a request.
- The script makes one fixed `GET /v2/insights` request: Radiohead as the interest signal, books as the target entity type.
- There are no retries, loops, fallback hosts, or redirect following.
- The API key is read only from the `QLOO_API_KEY` environment variable. Never put it in source, artifacts, logs, or chat.
- Response bytes are bounded. Successful responses are reduced to a compact schema/result summary; the full response body is not persisted.
- Artifacts contain a small sanitized `results.json` and expire after 3 days.

## Local checks (no API request)

Run the offline parser tests:

```sh
python -m unittest discover -s tests -v
python -m py_compile scripts/probe.py
```

These tests use synthetic payloads. They do not validate live API access or the actual Qloo response schema.

## Run the probe

1. Open the repository's **Actions** tab.
2. Select **Qloo probe** and click **Run workflow**.
3. Keep `mode=insights` and `max_requests=1`.
4. Download the `qloo-insights-results` artifact.
5. Inspect `results.json` for HTTP status, detected result collection, result count, a few entity fields, and explainability fields.

The workflow also has a dedicated sentinel-file push trigger. Do not create or push that sentinel unless you intend to spend one Qloo request. Do not rerun a failed request until its failure status and endpoint are understood.

## Endpoint and interpretation

The probe uses `https://hackathon.api.qloo.com/v2/insights`. It does not try alternate hosts automatically. Confirm the host against official hackathon onboarding materials before a live run.

A successful HTTP status confirms only that the endpoint returned successfully. It does not, by itself, prove that the response contains book recommendations or validate the cultural hypothesis.
