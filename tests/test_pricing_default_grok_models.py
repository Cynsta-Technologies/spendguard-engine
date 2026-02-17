import unittest

from spendguard_engine.pricing import DEFAULT_RATES, copy_rates


class TestPricingDefaultGrokModels(unittest.TestCase):
    def test_default_rates_include_grok_models(self):
        rates = copy_rates(DEFAULT_RATES)
        grok = rates.get("grok") or {}

        self.assertIn("grok-3", grok)
        self.assertIn("grok-3-latest", grok)
        self.assertIn("grok-3-fast-latest", grok)

        self.assertEqual(grok["grok-3"].input_cents_per_1m, 300)
        self.assertEqual(grok["grok-3"].output_cents_per_1m, 1500)
        self.assertEqual(grok["grok-3"].cached_input_cents_per_1m, 75)


if __name__ == "__main__":
    unittest.main()
