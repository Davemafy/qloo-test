"""Offline parsing checks for the public Igor deployment probe."""

import json
import unittest

from scripts.igor_live_smoke import check_model, check_qloo, last_turn_event


class DeploymentProbeTests(unittest.TestCase):
    def test_final_stream_event(self):
        payload = 'data: {"type":"state"}\n\ndata: {"type":"done","task":{"id":"test"}}\n\n'
        self.assertEqual(last_turn_event(payload)["task"]["id"], "test")

    def test_live_evidence_only_confirms_live_qloo(self):
        task = {
            "status": "ready",
            "error": None,
            "evidence": [
                {"kind": "cultural", "delivery": "CACHED"},
                {"kind": "cultural", "delivery": "LIVE"},
            ],
            "trace": [{"action": "cultural.discover", "requests": 3}],
        }
        report = check_qloo(task)
        self.assertEqual(report["status"], "live")
        self.assertEqual(report["discovery_requests"], 3)

    def test_scripted_interpreter_is_not_called_model(self):
        task = {"modelMode": "scripted", "trace": [{"action": "model.interpret", "requests": 0}]}
        self.assertEqual(check_model(task)["status"], "scripted_or_unconfirmed")

    def test_failed_model_is_not_reported_as_success(self):
        task = {"modelMode": "tool-calling", "trace": [{"action": "model.interpret.error", "requests": 1}]}
        self.assertEqual(check_model(task)["status"], "error")


if __name__ == "__main__":
    unittest.main()
