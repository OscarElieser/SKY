"""Tests: SKY native adaptation only uses observed counters, never grants authority."""
import unittest
from unittest.mock import patch

from neural_core import sky_adaptive_policy as policy


class NativeAdaptivePolicyTests(unittest.TestCase):
    def test_no_history_fails_closed(self):
        data = policy.reliability("planificador", {})
        self.assertEqual(data["status"], "insufficient_evidence")
        self.assertIsNone(data["success_rate"])
        self.assertFalse(data["can_execute"])

    def test_high_success_requires_enough_samples(self):
        short = policy.reliability("planificador", {"planificador": {"completed": 4, "failed": 0}})
        self.assertEqual(short["status"], "insufficient_evidence")
        larger = policy.reliability("planificador", {"planificador": {"completed": 20, "failed": 0}})
        self.assertEqual(larger["status"], "candidate_for_supervised_test")
        self.assertFalse(larger["can_execute"])
        self.assertGreater(larger["confidence_lower_bound"], .60)

    def test_failures_reduce_recommendation(self):
        x = policy.reliability("memoria", {"memoria": {"completed": 2, "failed": 18}})
        self.assertEqual(x["status"], "review_failures")
        self.assertLess(x["confidence_lower_bound"], .3)

    def test_poisoned_or_unknown_stats_do_not_escalate(self):
        for stats in ({"planificador": {"completed": -1, "failed": 0}},
                      {"planificador": {"completed": True, "failed": 0}},
                      {"planificador": {"completed": "999", "failed": 0}},
                      {"planificador": {"completed": 100000, "failed": 0}}):
            data = policy.reliability("planificador", stats)
            self.assertEqual(data["status"], "insufficient_evidence")
        self.assertEqual(policy.reliability("admin", {})["status"], "no_measured_role")

    def test_low_risk_uses_local_evidence_without_running_tools(self):
        stats = {"documentalista": {"completed": 30, "failed": 0}}
        with patch.object(policy, "_verified_stats", return_value=(stats, True)):
            result = policy.adaptive_plan("investigación sobre fuentes académicas")
        self.assertFalse(result["action_executed"])
        self.assertFalse(result["permission_granted"])
        self.assertFalse(result["model_provider_called"])
        self.assertFalse(result["input_stored"])
        self.assertEqual(result["role_reliability"]["status"], "candidate_for_supervised_test")
        self.assertFalse(result["review_required"])

    def test_high_risk_never_gains_permission_from_positive_feedback(self):
        stats = {"planificador": {"completed": 100, "failed": 0}}
        with patch.object(policy, "_verified_stats", return_value=(stats, True)):
            result = policy.adaptive_plan("elimina mis archivos del teléfono", device="android")
        self.assertEqual(result["classification"]["risk"], "alto")
        self.assertTrue(result["review_required"])
        self.assertFalse(result["permission_granted"])
        self.assertEqual(result["plan"]["executed_steps"], 0)

    def test_invalid_query_is_rejected(self):
        with self.assertRaises(ValueError):
            policy.adaptive_plan("x" * 3000)

    def test_failure_to_read_telemetry_does_not_claim_learning(self):
        with patch("neural_core.sky_neural_memory.execution_report", side_effect=OSError("offline")):
            result = policy.evolution_status()
        self.assertFalse(result["telemetry_available"])
        self.assertFalse(result["training_performed"])
        self.assertFalse(result["automatic_tool_execution"])

    def test_evolution_status_does_not_return_private_text(self):
        stats = {"memoria": {"completed": 1, "failed": 0}}
        with patch.object(policy, "_verified_stats", return_value=(stats, True)):
            result = policy.evolution_status()
        self.assertNotIn("prompt", str(result))
        self.assertFalse(result["model_weights_updated"])
        self.assertFalse(result["external_inference_required"])


if __name__ == "__main__":
    unittest.main()
