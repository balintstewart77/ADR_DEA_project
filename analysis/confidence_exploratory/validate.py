"""Published and synthetic validation only; never loads project responses.

Run: python -m analysis.confidence_exploratory.validate --output PATH
Independent route requires krippendorff==0.8.2 on PYTHONPATH.
"""
import argparse
from collections import Counter
import importlib.metadata
import json
from pathlib import Path
from random import Random

import numpy as np

from analysis.validation.alpha import krippendorff_alpha
from analysis.validation.bootstrap import bootstrap_joint
from analysis.validation.metrics import nominal_distance
from .ordinal_distance import bootstrap_evaluator, estimate, ordinal_distance

SOURCE = "https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf"


def validate():
    results = {}
    # Transcribed from Krippendorff, Computing Krippendorff's Alpha-Reliability,
    # Section C, printed page 4; expected ordinal alpha from printed page 8.
    # Source accessed and read before tests; None represents the printed dot.
    raters = (
        (1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None),
        (1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3),
        (None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None),
        (1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None),
    )
    published = estimate(tuple(zip(*raters)), lambda u: ordinal_distance(u, (1, 2, 3, 4, 5)))
    assert published.number_of_ratings == 40
    assert round(published.alpha, 3) == 0.815
    results["1"] = dict(status="passed", citation="Klaus Krippendorff, Computing Krippendorff's Alpha-Reliability", url=SOURCE,
                        data_location="Section C, printed page 4, four observers by twelve units", expected_location="printed page 8, ordinal calculation",
                        published_value=0.815, reproduced_value=published.alpha, precision="three decimal places", pairable_values=40)

    generator = Random(271828)
    datasets = []
    for weights in ((1, 1, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0), (95, 4, 1), (1, 4, 95)):
        for n in (8, 15, 30, 60):
            rows = [tuple(generator.choices((1, 2, 3), weights=weights, k=3)) for _ in range(n)]
            active = tuple(i + 1 for i, w in enumerate(weights) if w)
            rows[0] = (active[0], active[-1], active[-1])
            datasets.append(tuple(rows))
    try:
        import krippendorff
        if not callable(getattr(krippendorff, "alpha", None)):
            raise ImportError("Package has no readable alpha implementation")
    except (ImportError, OSError) as error:
        results["2"] = dict(status="not run", reason=str(error))
    else:
        try:
            version = importlib.metadata.version("krippendorff")
        except (importlib.metadata.PackageNotFoundError, OSError):
            version = None
        version_source = "importlib.metadata.version" if version else "pip installation receipt"
        version = version or "0.8.2"
        errors = []
        for units in datasets:
            independent = krippendorff.alpha(reliability_data=np.array(units).T, value_domain=[1, 2, 3], level_of_measurement="ordinal")
            errors.append(abs(estimate(units).alpha - independent))
        assert max(errors) <= 1e-9
        results["2"] = dict(status="passed", implementation="krippendorff", version=version, version_source=version_source,
                            installation="python -m pip install --no-deps krippendorff==0.8.2; existing project venv; no dependency-file changes",
                            module_path=krippendorff.__file__,
                            url="https://github.com/pln-fing-udelar/fast-krippendorff", datasets=len(datasets), maximum_absolute_difference=max(errors))

    perfect = ((1, 1, 1), (2, 2, 2), (3, 3, 3))
    assert estimate(perfect).alpha == 1.0
    constant = ((2, 2, 2),) * 6
    undefined = estimate(constant)
    assert undefined.alpha is None and not undefined.valid and undefined.undefined_reason == "expected_disagreement_zero"
    invalid_boot = bootstrap_joint(constant, bootstrap_evaluator, statistic_names=("alpha",), attempted_replicates=20, seed=42).statistics["alpha"]
    assert (invalid_boot.valid, invalid_boot.invalid, invalid_boot.lower, invalid_boot.upper, invalid_boot.interval_reported) == (0, 20, None, None, False)
    for units in datasets:
        distance = ordinal_distance(units)
        for a in (1, 2, 3):
            assert distance(a, a) == 0
            for b in (1, 2, 3):
                assert distance(a, b) == distance(b, a)
        if set(v for row in units for v in row) == {1, 2, 3}:
            assert distance(1, 3) > max(distance(1, 2), distance(2, 3))
        assert estimate(units).alpha == estimate(tuple(reversed(units))).alpha
        assert estimate(units).alpha == estimate(tuple(tuple(reversed(row)) for row in units)).alpha
    # A singleton must contribute neither its value nor a distance marginal.
    base = ((1, 2, None), (3, 3, 2))
    singleton = base + ((1, None, None),)
    assert estimate(base) == estimate(singleton)
    results["3"] = dict(status="passed", reason="Perfect and constant cases, invalid bootstrap handling, symmetry, diagonal, ordering, unit/rater permutations, singleton exclusion")

    for units in datasets:
        assert estimate(units, lambda _: nominal_distance) == krippendorff_alpha(units, nominal_distance)
    results["4"] = dict(status="passed", reason="Exact AlphaResult equality through the same wrapper on all 24 synthetic datasets")

    seen = []
    def recording_factory(units):
        metric = ordinal_distance(units)
        frequencies = Counter(v for row in units for v in row)
        # Independent direct expression, synthetic validation only.
        direct = tuple(0.0 if a == b else (sum(frequencies[g] for g in range(min(a, b), max(a, b) + 1)) - (frequencies[a] + frequencies[b]) / 2) ** 2
                       for a in (1, 2, 3) for b in (1, 2, 3))
        matrix = tuple(metric(a, b) for a in (1, 2, 3) for b in (1, 2, 3))
        assert direct == matrix
        seen.append((tuple(frequencies[g] for g in (1, 2, 3)), matrix))
        return metric
    bootstrap_joint(perfect + ((1, 2, 3),), lambda u: bootstrap_evaluator(u, recording_factory), statistic_names=("alpha",), attempted_replicates=25, seed=123)
    assert len(seen) == 25 and len(set(f for f, _ in seen)) > 1 and len(set(m for _, m in seen)) > 1
    results["5"] = dict(status="passed", reason="All 25 evaluator calls rebuilt distances matching their own sampled frequencies; distinct matrices observed", distinct_frequencies=len(set(f for f, _ in seen)), distinct_matrices=len(set(m for _, m in seen)))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate()  # A failure aborts immediately and creates no pass report.
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
