import unittest
from scripts.tracker import classify_categories, classify_relevance, build_plain_summary, is_technical_line, substantive_changed_lines

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

    def test_trace_ids_are_technical_noise(self):
        self.assertTrue(is_technical_line("This is the Trace Id: 5618df285b490822faa0aa40ebf5764d"))
        added, removed = substantive_changed_lines(
            ["This is the Trace Id: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"],
            ["This is the Trace Id: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        )
        self.assertEqual(added, [])
        self.assertEqual(removed, [])

    def test_legal_text_is_never_filtered_with_trace_noise(self):
        added, removed = substantive_changed_lines(
            ["This is the Trace Id: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "We may share personal data with service providers."],
            ["This is the Trace Id: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        )
        self.assertEqual(added, ["We may share personal data with service providers."])
        self.assertEqual(removed, [])

if __name__ == "__main__":
    unittest.main()
