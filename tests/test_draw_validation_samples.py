from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import yaml

from scripts import draw_validation_samples as sampler


NON_OFFICIAL_SEED = 314159


def rid(index: int) -> str:
    return f"{8000 + index // 1000:04d}/{index % 1000:03d}"


def make_inputs(
    *,
    population_n: int = 1200,
    hard_counts: tuple[int, int, int] = (150, 150, 150),
    forced_counts: tuple[int, int, int] = (2, 2, 2),
    exclusions_n: int = 22,
) -> sampler.ValidatedInputs:
    cleaned = pd.DataFrame({
        "record_id": [rid(i) for i in range(population_n)],
        "official_project_id": [rid(i) for i in range(population_n)],
    })
    exclusions = frozenset(rid(i) for i in range(exclusions_n))
    rows: list[dict[str, object]] = []
    position = exclusions_n
    for stratum, count, forced in zip(sampler.STRATA, hard_counts, forced_counts):
        for offset in range(count):
            rows.append({
                "record_id": rid(position),
                "official_project_id": rid(position),
                "hard_case_stratum": stratum,
                "accompanying_tag_disagreement": offset < forced,
            })
            position += 1
    hard = pd.DataFrame(rows)
    return sampler.ValidatedInputs(
        cleaned=cleaned,
        exclusions=exclusions,
        hard=hard,
        input_hashes={"cleaned_population": "a" * 64, "exclusion": "b" * 64, "disagreement_frame": "c" * 64},
        source_paths={"cleaned_population": "cleaned.csv", "exclusion": "exclusions.csv", "disagreement_frame": "hard.csv"},
    )


def signature(result: sampler.SamplingResult) -> dict[str, list[str]]:
    return {name: frame["record_id"].tolist() for name, frame in result.outputs.items()}


class SamplingDrawTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = make_inputs()

    def test_01_ordinary_full_draw(self) -> None:
        result = sampler.draw_samples(self.inputs, NON_OFFICIAL_SEED)
        self.assertEqual({name: len(frame) for name, frame in result.outputs.items()}, {
            "baseline_active": 150, "baseline_reserve": 100, "hard_active": 75, "hard_reserve": 50,
        })

    def test_02_deterministic_reproduction(self) -> None:
        self.assertEqual(signature(sampler.draw_samples(self.inputs, 10)), signature(sampler.draw_samples(self.inputs, 10)))

    def test_03_invariant_to_input_row_order(self) -> None:
        shuffled = sampler.ValidatedInputs(
            cleaned=self.inputs.cleaned.sample(frac=1, random_state=7),
            exclusions=self.inputs.exclusions,
            hard=self.inputs.hard.sample(frac=1, random_state=8),
            input_hashes=self.inputs.input_hashes,
            source_paths=self.inputs.source_paths,
        )
        self.assertEqual(signature(sampler.draw_samples(self.inputs, 11)), signature(sampler.draw_samples(shuffled, 11)))

    def test_04_different_nonofficial_seeds_change_valid_draw(self) -> None:
        first = sampler.draw_samples(self.inputs, 12)
        second = sampler.draw_samples(self.inputs, 13)
        self.assertNotEqual(signature(first), signature(second))
        self.assertTrue(all(second.assertions.values()))

    def test_05_exclusions_removed(self) -> None:
        selected = set().union(*(set(frame["record_id"]) for frame in sampler.draw_samples(self.inputs, 14).outputs.values()))
        self.assertFalse(selected & self.inputs.exclusions)

    def test_06_baseline_active_and_reserve_disjoint(self) -> None:
        result = sampler.draw_samples(self.inputs, 15)
        self.assertFalse(set(result.outputs["baseline_active"]["record_id"]) & set(result.outputs["baseline_reserve"]["record_id"]))

    def test_07_hard_depletion_by_baseline_active(self) -> None:
        result = sampler.draw_samples(self.inputs, 16)
        hard_ids = set(self.inputs.hard["record_id"])
        self.assertTrue(set(result.outputs["baseline_active"]["record_id"]) & hard_ids)

    def test_08_hard_depletion_by_baseline_reserve(self) -> None:
        result = sampler.draw_samples(self.inputs, 17)
        hard_ids = set(self.inputs.hard["record_id"])
        self.assertTrue(set(result.outputs["baseline_reserve"]["record_id"]) & hard_ids)

    def test_09_forced_accompanying_tags_included(self) -> None:
        result = sampler.draw_samples(self.inputs, 18)
        baseline = set(result.outputs["baseline_active"]["record_id"]) | set(result.outputs["baseline_reserve"]["record_id"])
        forced = set(self.inputs.hard.loc[self.inputs.hard["accompanying_tag_disagreement"], "record_id"]) - baseline
        self.assertTrue(forced.issubset(set(result.outputs["hard_active"]["record_id"])))

    def test_10_forced_cases_count_toward_source_quota(self) -> None:
        result = sampler.draw_samples(self.inputs, 19)
        hard = result.outputs["hard_active"]
        self.assertEqual(hard["hard_case_stratum"].value_counts().to_dict(), {"domain_only": 25, "purpose_only": 25, "both": 25})
        self.assertTrue(hard.loc[hard["forced_into_active_hard"], "accompanying_tag_disagreement"].all())

    def test_11_forced_overflow_fails(self) -> None:
        inputs = make_inputs(hard_counts=(40, 40, 40), forced_counts=(26, 0, 0))
        plan = sampler.SamplingPlan(baseline_active_n=0, baseline_reserve_n=0)
        with self.assertRaisesRegex(sampler.SamplingError, "exceed quota"):
            sampler.draw_samples(inputs, 20, plan=plan)

    def test_12_ordinary_reserve_is_17_17_16(self) -> None:
        initial, final, _, _, shortfall = sampler.allocate_hard_reserve({s: 100 for s in sampler.STRATA}, sampler.create_rng(21))
        self.assertEqual(sorted(initial.values()), [16, 17, 17])
        self.assertEqual(initial, final)
        self.assertEqual(shortfall, 0)

    def test_13_sixteen_seat_stratum_is_deterministic(self) -> None:
        first = sampler.allocate_hard_reserve({s: 100 for s in sampler.STRATA}, sampler.create_rng(22))[0]
        second = sampler.allocate_hard_reserve({s: 100 for s in sampler.STRATA}, sampler.create_rng(22))[0]
        self.assertEqual(first, second)
        self.assertEqual(sum(value == 16 for value in first.values()), 1)

    def test_14_one_stratum_shortage_reallocated_evenly(self) -> None:
        _, final, _, actions, shortfall = sampler.allocate_hard_reserve({"domain_only": 10, "purpose_only": 30, "both": 30}, sampler.create_rng(23))
        self.assertEqual(sum(final.values()), 50)
        self.assertEqual(final["domain_only"], 10)
        self.assertLessEqual(abs(final["purpose_only"] - final["both"]), 1)
        self.assertTrue(actions)
        self.assertEqual(shortfall, 0)

    def test_15_two_strata_shortages_reallocate(self) -> None:
        _, final, _, _, shortfall = sampler.allocate_hard_reserve({"domain_only": 8, "purpose_only": 9, "both": 50}, sampler.create_rng(24))
        self.assertEqual(final, {"domain_only": 8, "purpose_only": 9, "both": 33})
        self.assertEqual(shortfall, 0)

    def test_16_total_reserve_shortfall_documented(self) -> None:
        _, final, _, _, shortfall = sampler.allocate_hard_reserve({"domain_only": 5, "purpose_only": 6, "both": 7}, sampler.create_rng(25))
        self.assertEqual(sum(final.values()), 18)
        self.assertEqual(shortfall, 32)

    def test_17_active_stratum_below_25_fails(self) -> None:
        inputs = make_inputs(hard_counts=(24, 30, 30), forced_counts=(0, 0, 0))
        plan = sampler.SamplingPlan(baseline_active_n=0, baseline_reserve_n=0)
        with self.assertRaisesRegex(sampler.SamplingError, "below quota"):
            sampler.draw_samples(inputs, 26, plan=plan)

    def test_18_exact_stratum_exhaustion_is_valid(self) -> None:
        inputs = make_inputs(hard_counts=(25, 25, 25), forced_counts=(0, 0, 0))
        plan = sampler.SamplingPlan(baseline_active_n=0, baseline_reserve_n=0)
        result = sampler.draw_samples(inputs, 27, plan=plan)
        self.assertEqual(len(result.outputs["hard_reserve"]), 0)
        self.assertEqual(result.metadata["hard_reserve_unfilled_shortfall"], 50)

    def test_19_duplicate_record_ids_fail(self) -> None:
        with self.assertRaisesRegex(sampler.SamplingError, "Duplicate"):
            sampler._validate_ids(pd.Series([rid(1), rid(1)]), "toy")

    def test_20_dirty_record_ids_fail(self) -> None:
        for value in [" " + rid(1), rid(1) + "\t", rid(1) + "\u00a0"]:
            with self.subTest(value=repr(value)), self.assertRaisesRegex(sampler.SamplingError, "Whitespace/control"):
                sampler._validate_ids(pd.Series([value]), "toy")


class InputAndSafetyTests(unittest.TestCase):
    def _write_inputs(self, directory: Path, *, missing_exclusion: bool = False, unknown: bool = False, inconsistent: bool = False) -> tuple[Path, Path, Path]:
        cleaned_path = directory / "cleaned.csv"
        exclusion_path = directory / "exclusions.csv"
        hard_path = directory / "hard.csv"
        pd.DataFrame({"Record ID": [rid(1), rid(2)], "Project ID": [rid(1), rid(2)]}).to_csv(cleaned_path, index=False)
        pd.DataFrame({"record_id": [rid(9) if missing_exclusion else rid(1)]}).to_csv(exclusion_path, index=False)
        pd.DataFrame({
            "Record ID": [rid(2)], "Project ID": [rid(2)],
            "disagreement_layer": ["mystery" if unknown else "domain"],
            "domains_exact_match": [True if inconsistent else False],
            "purposes_exact_match": [True], "covid_tag_match": [True],
            "disparities_tag_match": [True], "tag_set_match": [True],
            "tag_only_disagreement": [False], "DISAGREE": [True],
        }).to_csv(hard_path, index=False)
        return cleaned_path, exclusion_path, hard_path

    def test_21_missing_excluded_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._write_inputs(Path(tmp), missing_exclusion=True)
            with self.assertRaisesRegex(sampler.SamplingError, "Excluded IDs absent"):
                sampler.validate_inputs(*paths)

    def test_22_unknown_stratum_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._write_inputs(Path(tmp), unknown=True)
            with self.assertRaisesRegex(sampler.SamplingError, "Unknown hard-case stratum"):
                sampler.validate_inputs(*paths)

    def test_23_inconsistent_tag_or_stratum_flags_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._write_inputs(Path(tmp), inconsistent=True)
            with self.assertRaisesRegex(sampler.SamplingError, "stratum/label-match inconsistency"):
                sampler.validate_inputs(*paths)

    def test_24_check_writes_nothing_and_creates_no_rng(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sampler, "create_rng", side_effect=AssertionError("RNG created")):
            before = list(Path(tmp).iterdir())
            self.assertEqual(sampler.main(["--check"]), 0)
            self.assertEqual(before, list(Path(tmp).iterdir()))

    def test_25_validate_real_inputs_writes_nothing_and_creates_no_rng(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sampler, "create_rng", side_effect=AssertionError("RNG created")):
            before = list(Path(tmp).iterdir())
            self.assertEqual(sampler.main(["--validate-real-inputs"]), 0)
            self.assertEqual(before, list(Path(tmp).iterdir()))

    def test_26_official_seed_real_paths_rejected_without_receipt(self) -> None:
        args = ["--execute-official-draw", "--cleaned", str(sampler.ROOT / sampler.REAL_CLEANED_PATH), "--exclusions", str(sampler.ROOT / sampler.REAL_EXCLUSION_PATH), "--disagreement", str(sampler.ROOT / sampler.REAL_HARD_PATH), "--output-directory", str(sampler.ROOT / sampler.RESTRICTED_SAMPLING_ROOT / "future"), "--seed", str(sampler.OFFICIAL_SEED)]
        with self.assertRaisesRegex(sampler.SamplingError, "registration-receipt"):
            sampler.main(args)

    def _guard_fixture(self, root: Path) -> tuple[sampler.ValidatedInputs, Path, Path, Path]:
        spec = root / "spec.yaml"
        spec.write_text("guard-test\n", encoding="utf-8")
        inputs = make_inputs()
        output = root / sampler.RESTRICTED_SAMPLING_ROOT / "official"
        receipt = root / "receipt.json"
        expected = {"sampling_specification": sampler.sha256_file(spec), **inputs.input_hashes}
        receipt.write_text(json.dumps({"osf_registration_identifier_or_url": "https://osf.invalid/registered", "registration_timestamp": "2030-01-01T00:00:00Z", "frozen_git_commit": "abc123", "gate_2_passed": True, "expected_hashes": expected}), encoding="utf-8")
        manifest = root / sampler.PROTOCOL_MANIFEST_PATH
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            "artefact_group,current_implementation_basis,frozen,registered,official_sample_draw_authorised,registration_identifier,registration_timestamp,implementation_last_checked_commit\n"
            "00_protocol,true,true,true,true,https://osf.invalid/registered,2030-01-01T00:00:00Z,abc123\n",
            encoding="utf-8",
        )
        return inputs, spec, output, receipt

    def test_27_frozen_v1_0_manifest_blocks_draw_until_registration(self) -> None:
        receipt = {
            "osf_registration_identifier_or_url": "synthetic",
            "registration_timestamp": "2030-01-01T00:00:00Z",
            "frozen_git_commit": "a" * 40,
        }
        with self.assertRaisesRegex(sampler.SamplingError, "not registered"):
            sampler.validate_protocol_draw_authorisation(
                sampler.ROOT / sampler.PROTOCOL_MANIFEST_PATH, receipt
            )

    def test_28_official_guard_rejects_dirty_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs, spec, output, receipt = self._guard_fixture(Path(tmp))
            with self.assertRaisesRegex(sampler.SamplingError, "clean Git worktree"):
                sampler.validate_official_guard(receipt_path=receipt, output_directory=output, confirmation_token=sampler.CONFIRMATION_TOKEN, specification_path=spec, inputs=inputs, root=Path(tmp), head_commit="abc123", worktree_clean=False)

    def test_29_official_guard_rejects_head_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs, spec, output, receipt = self._guard_fixture(Path(tmp))
            with self.assertRaisesRegex(sampler.SamplingError, "frozen receipt commit"):
                sampler.validate_official_guard(receipt_path=receipt, output_directory=output, confirmation_token=sampler.CONFIRMATION_TOKEN, specification_path=spec, inputs=inputs, root=Path(tmp), head_commit="different", worktree_clean=True)

    def test_30_official_guard_rejects_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs, spec, output, receipt = self._guard_fixture(Path(tmp))
            output.mkdir(parents=True)
            (output / "baseline_active.csv").write_text("identity\n", encoding="utf-8")
            with self.assertRaisesRegex(sampler.SamplingError, "already contains"):
                sampler.validate_official_guard(receipt_path=receipt, output_directory=output, confirmation_token=sampler.CONFIRMATION_TOKEN, specification_path=spec, inputs=inputs, root=Path(tmp), head_commit="abc123", worktree_clean=True)

    def test_31_output_metadata_and_hashes_match(self) -> None:
        result = sampler.draw_samples(make_inputs(), 28)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "synthetic"
            hashes = sampler.write_sampling_outputs(result, output, repository_commit="abc123", specification_path="spec.yaml", specification_hash="d" * 64, input_hashes={"cleaned_population": "a" * 64}, input_paths={"cleaned_population": "toy.csv"}, timestamp="2030-01-01T00:00:00Z")
            metadata = json.loads((output / "sampling_metadata.json").read_text(encoding="utf-8"))
            for filename, digest in metadata["output_hashes"].items():
                self.assertEqual(digest, sampler.sha256_file(output / filename))
            self.assertEqual(hashes["sampling_metadata.json"], sampler.sha256_file(output / "sampling_metadata.json"))

    def test_32_specification_and_output_schema_parse(self) -> None:
        specification = yaml.safe_load((sampler.ROOT / sampler.SPECIFICATION_PATH).read_text(encoding="utf-8"))
        schema = json.loads((sampler.ROOT / "preregistration/package/04_exclusions_and_sampling/sampling_output_schema.json").read_text(encoding="utf-8"))
        self.assertEqual(
            specification["inputs"]["exclusion_sha256"],
            sampler.sha256_file(sampler.ROOT / sampler.REAL_EXCLUSION_PATH),
        )
        self.assertIn("canonical UTF-8-with-BOM LF", specification["inputs"]["exclusion_hash_basis"])
        self.assertEqual(
            specification["inputs"]["disagreement_frame_sha256"],
            sampler.sha256_file(sampler.ROOT / sampler.REAL_HARD_PATH),
        )
        self.assertIn("canonical UTF-8-with-BOM LF", specification["inputs"]["disagreement_frame_hash_basis"])
        self.assertFalse(specification["prospective_boundary"]["official_draw_executed"])
        self.assertTrue(specification["protocol_basis"]["frozen"])
        self.assertFalse(specification["protocol_basis"]["registered"])
        self.assertFalse(specification["project_owner_review"]["fixed_reserve_exists"])
        self.assertIn("record_fields", schema["required"])

    def test_33_runbook_uses_placeholders_not_fabricated_receipt(self) -> None:
        runbook = (sampler.ROOT / "preregistration/package/04_exclusions_and_sampling/official_sampling_runbook.md").read_text(encoding="utf-8")
        self.assertIn("Do not fabricate", runbook)
        self.assertNotIn("--registration-receipt fake", runbook)


if __name__ == "__main__":
    unittest.main()
