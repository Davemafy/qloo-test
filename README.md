# Qloo API Probe Harness

A deliberately quota-conservative test harness for the Qloo hackathon API.

## Safety model

- No Qloo requests run on push, pull requests, schedules, or deployment.
- The workflow is started manually from GitHub Actions.
- Default mode is a single `/search` smoke test.
- Discovery mode is disabled in the initial version; it will be added only after the smoke response is inspected.
- The API key is read only from the `QLOO_API_KEY` GitHub Actions secret. Never put it in source, artifacts, logs, or chat.
- Responses are sanitized before being uploaded as an artifact.

## Setup

1. In repository Settings → Secrets and variables → Actions, create `QLOO_API_KEY` with the key supplied for the hackathon.
2. Open the **Qloo probe** workflow under Actions.
3. Choose **Run workflow**. Keep `mode` set to `smoke` and confirm the request budget is `1`.
4. Download the `qloo-probe-results` artifact and inspect `results.json`.

## Endpoint

The harness uses `https://hackathon.api.qloo.com`. Confirm the host against the raw official hackathon onboarding email before running. It does not try alternate hosts automatically.

## Important

This repository is for controlled API experiments, not production use. A successful HTTP response confirms only basic access; it does not validate the insights endpoint or prove any cultural hypothesis.
