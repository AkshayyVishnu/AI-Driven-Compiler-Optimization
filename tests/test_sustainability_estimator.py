import unittest

from src.sustainability import estimate_run_footprint


class SustainabilityEstimatorTests(unittest.TestCase):
    def test_optimize_estimate_is_positive_and_labeled(self):
        estimate = estimate_run_footprint(
            "optimize",
            "int main() {\n  int x;\n  return 0;\n}\n",
            {
                "transformations": [{"type": "initialize_variable"}],
                "stage_timings": {"rule_s": 0.15, "llm_s": 0.0},
            },
            use_llm=False,
        )

        self.assertEqual(estimate["action"], "optimize")
        self.assertEqual(estimate["action_label"], "Optimization")
        self.assertGreater(estimate["total_energy_mwh"], 0.0)
        self.assertGreater(estimate["total_emissions_mg"], 0.0)
        self.assertIn("mWh", estimate["energy_display"])
        self.assertIn("CO2e", estimate["emissions_display"])

    def test_verify_estimate_reflects_stage_time(self):
        small = estimate_run_footprint(
            "verify",
            "int main(){return 0;}",
            {"stage_timings": {"parallel_checks_s": 0.2, "llm_s": 0.0}},
            use_llm=False,
        )
        large = estimate_run_footprint(
            "verify",
            "int main(){return 0;}",
            {"stage_timings": {"parallel_checks_s": 3.0, "llm_s": 0.0}},
            use_llm=False,
        )

        self.assertGreater(
            large["total_energy_mwh"],
            small["total_energy_mwh"],
        )
        self.assertGreater(
            large["total_emissions_mg"],
            small["total_emissions_mg"],
        )

    def test_pipeline_estimate_uses_pipeline_label(self):
        estimate = estimate_run_footprint(
            "pipeline",
            "int main(){return 0;}",
            {
                "all_findings": [{"type": "uninitialized_variable"}],
                "transformations": [{"type": "initialize_variable"}],
                "stage_timings": {
                    "analysis": {"rule_s": 0.1},
                    "optimization": {"rule_s": 0.2},
                    "verification": {"parallel_checks_s": 0.5},
                    "security": {"total_s": 0.05},
                },
            },
            use_llm=False,
        )

        self.assertEqual(estimate["action_label"], "Full Pipeline")
        self.assertGreater(estimate["total_energy_mwh"], 0.0)


if __name__ == "__main__":
    unittest.main()
