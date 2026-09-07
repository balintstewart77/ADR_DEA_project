import unittest

from .assessment import ALLOWED_DECISIONS, classify, decision


class ScopeDecisionTests(unittest.TestCase):
    def item(self, unit, population="baseline", count_validation="valid_integer_counts", existing="not_exported", equivalent=None):
        return {"observational_unit_class":unit,"population":population,"count_validation":count_validation,
                "existing_interval":{"status":existing},"equivalent_existing_interval":equivalent}

    def test_decision_boundaries(self):
        self.assertEqual(decision(self.item("record_binary"))[0],"candidate_for_later_authorised_wilson")
        self.assertEqual(decision(self.item("individual_coder_binary"))[0],"candidate_for_later_authorised_wilson")
        self.assertEqual(decision(self.item("pooled_coder_responses"))[0],"methodological_decision_required")
        self.assertEqual(decision(self.item("structural_ratio"))[0],"no_inferential_interval_proposed")
        self.assertEqual(decision(self.item("record_binary",population="hard_case"))[0],"excluded_nonbaseline")
        self.assertEqual(decision(self.item("record_binary",existing="reported"))[0],"already_exported")

    def test_pooled_all_coder_classification(self):
        unit,sampling,pooled,family=classify("sufficiency_response_distribution",{"coder":"all"})
        self.assertEqual(unit,"pooled_coder_responses");self.assertTrue(pooled)
        unit,sampling,pooled,family=classify("sufficiency_response_distribution",{"coder":"C01"})
        self.assertEqual(unit,"individual_coder_binary");self.assertFalse(pooled)

    def test_decisions_are_registered(self):
        for unit in ("record_binary","individual_coder_binary","pooled_coder_responses","structural_ratio","other_or_unclear"):
            self.assertIn(decision(self.item(unit))[0],ALLOWED_DECISIONS)


if __name__=="__main__":
    unittest.main()
