"""Synthetic tests for the primary-versus-secondary agreement helpers (no restricted data)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from compare_formal_secondary import MODEL, kappa, mechanism_keys, rate, summarise  # noqa: E402


def finding(family=MODEL, code="11", labels=""):
    return {"family": family, "mechanism_code": code, "labels": labels}


def record(model=(True, True), mech=(["11"], ["11"]), fams=None, closure=("1", "1")):
    fams = fams or ([MODEL] if model[0] else [], [MODEL] if model[1] else [])
    return {"s1_component_agreement": {"dom": {"evidence": True, "best": True, "defensible": False}},
            "s1_conflict_any": (True, True), "closure": closure, "families": fams, "model_finding": model,
            "mechanisms": mech, "release": ([], [], []), "masking_failure": "no"}


class AgreementHelpers(unittest.TestCase):
    def test_mechanism_keys_split_general_mechanisms_by_label(self):
        keys = mechanism_keys([finding(code="24", labels="Education & Skills; Crime & Justice"), finding(code="11"),
                               finding(family="Coder rule-application problem", code="11"), finding(code="")])
        self.assertEqual(keys, {"24 | Education & Skills", "24 | Crime & Justice", "11", "typed: (none)"})
        self.assertEqual(mechanism_keys([finding(code="25")]), {"25 | (labels not recorded)"})

    def test_rate_and_kappa(self):
        self.assertEqual(rate([True, True, False, True])["agree"], 3)
        self.assertEqual(rate([])["n"], 0)
        self.assertEqual(kappa([(True, True), (False, False)]), 1.0)
        self.assertIsNone(kappa([(True, True), (True, True)]))  # no variation: kappa undefined
        self.assertAlmostEqual(kappa([(True, True), (True, False), (False, False), (False, False)]), 0.5)

    def test_summary_counts_disagreement_directions(self):
        s = summarise([record(), record(model=(False, True), mech=([], ["11"])), record(model=(True, False), mech=(["27"], []))])
        m = s["model_finding_presence"]
        self.assertEqual((m["agree"], m["n"], m["both"], m["primary_only"], m["secondary_only"]), (1, 3, 1, 1, 1))
        self.assertEqual(s["model_mechanisms_exact_where_both_found"]["n"], 1)
        self.assertEqual(s["stage1_by_component"]["defensible"]["agree"], 0)


if __name__ == "__main__":
    unittest.main()
