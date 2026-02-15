import os
import unittest

from spendguard_engine.pricing import DEFAULT_RATES, copy_rates


class TestPricingDefaultOpenAIReasoningModels(unittest.TestCase):
    def setUp(self):
        self._source = os.environ.get("CAP_PRICING_SOURCE")

    def tearDown(self):
        if self._source is None:
            os.environ.pop("CAP_PRICING_SOURCE", None)
        else:
            os.environ["CAP_PRICING_SOURCE"] = self._source

    def test_default_rates_include_openai_reasoning_models(self):
        rates = copy_rates(DEFAULT_RATES)
        openai = rates.get("openai") or {}

        # Keep this test in sync with spendguard_engine/pricing.py.
        self.assertIn("gpt-5.2", openai)
        self.assertIn("gpt-5.2-pro", openai)
        self.assertIn("o3-mini", openai)
        self.assertIn("o3", openai)
        self.assertIn("o3-pro", openai)
        self.assertIn("o3-deep-research", openai)
        self.assertIn("o1-mini", openai)
        self.assertIn("o1", openai)

        self.assertEqual(openai["gpt-5.2"].input_cents_per_1m, 175)
        self.assertEqual(openai["gpt-5.2"].output_cents_per_1m, 1400)
        self.assertEqual(openai["gpt-5.2-pro"].input_cents_per_1m, 2100)
        self.assertEqual(openai["gpt-5.2-pro"].output_cents_per_1m, 16800)

        self.assertEqual(openai["o3-mini"].input_cents_per_1m, 110)
        self.assertEqual(openai["o3-mini"].output_cents_per_1m, 440)
        self.assertEqual(openai["o3-mini"].cached_input_cents_per_1m, 55)

        self.assertEqual(openai["o3-pro"].input_cents_per_1m, 2000)
        self.assertEqual(openai["o3-pro"].output_cents_per_1m, 8000)


if __name__ == "__main__":
    unittest.main()

