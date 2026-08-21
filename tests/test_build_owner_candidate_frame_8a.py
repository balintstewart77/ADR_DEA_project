from __future__ import annotations

import unittest
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.validation.build_owner_candidate_frame_8a import (
    _given_names_consistent,
    _merge_permitted,
    candidate_key,
    resolve_candidate_identities,
)


def _row(
    record_id: str, name: str, identity_key: str, institution: str,
) -> dict[str, object]:
    return {
        "record_id": record_id,
        "project_id": record_id,
        "researcher_displayed": name,
        "researcher_normalised": name,
        "researcher_identity_key": identity_key,
        "entity_status": "person_candidate",
        "entity_status_reason": "synthetic person",
        "eligible_as_index_researcher": 1,
        "source_name_string": name,
        "source_name_capture_status": "verbatim_source_slice",
        "institution_as_registered": institution,
        "institution_capture_status": "verbatim_source_slice" if institution else "empty",
        "institution_normalised": institution,
        "institution_match_status": "identity" if institution else "empty",
    }


class OwnerCandidateFrame8ATest(unittest.TestCase):
    def test_given_names_accept_initial_or_absent_middle_but_reject_conflict(self) -> None:
        self.assertTrue(_given_names_consistent(("s", "g"), ("stuart", "george")))
        self.assertTrue(_given_names_consistent(("stuart",), ("stuart", "george")))
        self.assertFalse(_given_names_consistent(("stuart", "j"), ("stuart", "george")))

    def test_v11_merge_requires_matching_nonmissing_institution(self) -> None:
        frame = pd.DataFrame([
            _row("SYN-1", "Stuart McIntyre", "stuart mcintyre", "University of Strathclyde"),
            _row("SYN-2", "Stuart George McIntyre", "stuart george mcintyre", "University of Strathclyde"),
            _row("SYN-3", "Stuart McIntyre", "stuart mcintyre", "Different University"),
            _row("SYN-4", "Stuart McIntyre", "stuart mcintyre", ""),
        ])
        resolved, evidence = resolve_candidate_identities(frame)

        self.assertEqual(
            resolved.loc[
                resolved.record_id.isin(["SYN-1", "SYN-2"]), "candidate_key"
            ].nunique(),
            1,
        )
        self.assertEqual(resolved["candidate_key"].nunique(), 3)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(
            set(evidence.iloc[0][["source_name_string_a", "source_name_string_b"]]),
            {"Stuart McIntyre", "Stuart George McIntyre"},
        )
        self.assertFalse(
            _merge_permitted(
                "Stuart J. McIntyre", "Stuart George McIntyre",
                "University of Strathclyde",
            )
        )

    def test_candidate_key_is_stable_and_position_independent(self) -> None:
        identity = "example person|||example university|||stable-signature"
        self.assertEqual(candidate_key(identity), candidate_key(identity))
        self.assertTrue(candidate_key(identity).startswith("CAND_"))


if __name__ == "__main__":
    unittest.main()
