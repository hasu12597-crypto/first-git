import json
import os
import tempfile
import unittest

from metrics import calculate_dora_metrics


class DORAMetricsTest(unittest.TestCase):
    def test_empty_data_returns_nulls_with_reasons(self):
        metrics = calculate_dora_metrics([], [], days=7)

        self.assertIsNone(metrics["lead_time_hours"])
        self.assertIsNone(metrics["deployment_frequency_per_week"])
        self.assertIsNone(metrics["mttr_hours"])
        self.assertIsNone(metrics["change_failure_rate_value"])
        self.assertIn("reason", metrics["lead_time"])
        self.assertIn("reason", metrics["deployment_frequency"])
        self.assertIn("reason", metrics["mttr"])
        self.assertIn("reason", metrics["change_failure_rate"])

    def test_sample_data_is_calculated(self):
        deployments = [
            {"id": "d1", "status": "success", "started_at": "2026-09-01T09:00:00Z", "deployed_at": "2026-09-01T10:30:00Z"},
            {"id": "d2", "status": "success", "started_at": "2026-09-08T08:00:00Z", "deployed_at": "2026-09-08T10:00:00Z"},
            {"id": "d3", "status": "failed", "started_at": "2026-09-12T07:00:00Z", "deployed_at": "2026-09-12T07:30:00Z"},
        ]
        incidents = [
            {"id": "i1", "status": "resolved", "started_at": "2026-09-03T00:00:00Z", "resolved_at": "2026-09-03T04:00:00Z"},
            {"id": "i2", "status": "resolved", "started_at": "2026-09-09T06:00:00Z", "resolved_at": "2026-09-09T08:00:00Z"},
        ]

        metrics = calculate_dora_metrics(deployments, incidents, days=7, reference_time="2026-09-14T00:00:00Z")

        self.assertAlmostEqual(metrics["lead_time_hours"], 1.75, places=2)
        self.assertAlmostEqual(metrics["deployment_frequency_per_week"], 2.0, places=2)
        self.assertAlmostEqual(metrics["mttr_hours"], 3.0, places=2)
        self.assertAlmostEqual(metrics["change_failure_rate_value"], 0.3333333333, places=4)


if __name__ == "__main__":
    unittest.main()
