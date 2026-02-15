import unittest

from spendguard_engine.providers.gemini_provider import extract_gemini_usage


class TestGeminiProvider(unittest.TestCase):
    def test_extract_usage(self):
        payload = {"usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 34}}
        self.assertEqual(extract_gemini_usage(payload), (12, 34))


if __name__ == "__main__":
    unittest.main()
