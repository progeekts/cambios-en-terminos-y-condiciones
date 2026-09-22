import unittest
from scripts.tracker import classify_categories, classify_relevance, build_plain_summary, extract_effective_date, semantic_fingerprint, diff_fingerprint

class TrackerClassifierTests(unittest.TestCase):
    def test_privacy_and_retention(self):
        categories = classify_categories(["We retain personal data until account deletion."], [])
        self.assertIn("Datos personales", categories)
        self.assertIn("Conservación y eliminación", categories)

    def test_ai_and_third_parties_are_high_relevance(self):
        categories = classify_categories(["We may share data with third parties to train our models."], [])
        self.assertEqual(classify_relevance(categories, 1, 0), "Alta")

    def test_plain_summary_is_non_legalistic(self):
        text = build_plain_summary(["Precios, pagos y suscripciones"], 3, 2)
        self.assertIn("precios, cobros, renovaciones o suscripciones", text)
        self.assertIn("resumen es automático", text)

    def test_effective_date_spanish(self):
        self.assertEqual(extract_effective_date("Condiciones\nA partir del 1 de enero de 2025\nTexto"), "1 de enero de 2025")

    def test_effective_date_english(self):
        self.assertEqual(extract_effective_date("Privacy\nLast updated: February 14, 2026\nText"), "February 14, 2026")

    def test_effective_date_does_not_cross_lines(self):
        self.assertIsNone(extract_effective_date("Last updated:\nWhat's new\nSeptember 2026"))

    def test_semantic_fingerprint_ignores_line_order(self):
        self.assertEqual(semantic_fingerprint("Uno\nDos"), semantic_fingerprint("Dos\nUno"))

    def test_diff_fingerprint_is_stable_for_reordered_diff(self):
        a = diff_fingerprint("policy", ["Nueva A", "Nueva B"], ["Vieja A"])
        b = diff_fingerprint("policy", ["Nueva B", "Nueva A"], ["Vieja A"])
        self.assertEqual(a, b)

if __name__ == "__main__":
    unittest.main()
