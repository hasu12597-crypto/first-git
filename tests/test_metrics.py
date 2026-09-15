import unittest
import urllib.error
from unittest.mock import patch

import metrics
from metrics import build_weekly_report, calculate_dora_metrics


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
        self.assertAlmostEqual(metrics["deployment_frequency_per_week"], 1.0, places=2)
        self.assertAlmostEqual(metrics["mttr_hours"], 3.0, places=2)
        self.assertAlmostEqual(metrics["change_failure_rate_value"], 0.3333333333, places=4)

    def test_weekly_report_includes_null_and_reason_guidance(self):
        metrics = calculate_dora_metrics([], [], days=7)
        report = build_weekly_report(metrics)

        self.assertIn("null", report)
        self.assertIn("reason", report.lower())
        self.assertIn("Lead Time", report)
        self.assertIn("MTTR", report)

    def test_collection_errors_are_visible_in_report(self):
        metrics = calculate_dora_metrics(
            [],
            [],
            collection_errors=[
                {
                    "source": "github_deployments",
                    "type": "http_error",
                    "status": 403,
                    "message": "Resource not accessible by integration",
                }
            ],
        )
        report = build_weekly_report(metrics)

        self.assertEqual(metrics["collection_errors"][0]["status"], 403)
        self.assertIn("github_deployments", report)
        self.assertIn("403", report)
        self.assertIn("Resource not accessible", report)

    def test_deployments_api_403_is_returned_as_error(self):
        error = urllib.error.HTTPError(
            "https://api.github.com/repos/example/repo/deployments",
            403,
            "Forbidden",
            {},
            None,
        )

        with patch.object(metrics, "GITHUB_TOKEN", "token"), patch("urllib.request.urlopen", side_effect=error):
            deployments, collection_error = metrics.fetch_github_pages_deployments("example/repo")

        self.assertEqual(deployments, [])
        self.assertEqual(collection_error["type"], "http_error")
        self.assertEqual(collection_error["status"], 403)
        self.assertEqual(collection_error["url"], "https://api.github.com/repos/example/repo/deployments")

    def test_evidence_and_subminute_lead_time_are_explicit(self):
        deployments = [
            {
                "id": "pages-1",
                "status": "success",
                "commit_sha": "abc",
                "commit_timestamp": "2026-09-15T06:07:00Z",
                "deployed_at": "2026-09-15T06:07:27Z",
                "environment": "github-pages",
            },
            {
                "id": "pages-2",
                "status": "failure",
                "commit_timestamp": "2026-09-15T06:08:00Z",
                "deployed_at": None,
                "environment": "github-pages",
            },
        ]

        metrics = calculate_dora_metrics(deployments, [], reference_time="2026-09-15T06:10:00Z")
        report = build_weekly_report(metrics)

        self.assertAlmostEqual(metrics["lead_time_hours"], 27 / 3600, places=6)
        self.assertEqual(metrics["deployment_frequency_per_week"], 1.0)
        self.assertEqual(metrics["change_failure_rate_value"], 0.5)
        self.assertEqual(metrics["deployment_evidence"]["record_count"], 2)
        self.assertEqual(metrics["deployment_evidence"]["unique_record_count"], 2)
        self.assertIn("27.0 seconds", report)


if __name__ == "__main__":
    unittest.main()
