"""Common-complete-case replacement-panel construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Hashable, Iterable, TypeVar

from .alpha import AlphaResult, krippendorff_alpha
from .bootstrap import StatisticValue


T = TypeVar("T", bound=Hashable)


@dataclass(frozen=True)
class DimensionPanel(Generic[T]):
    record_id: str
    coder_a: T | None
    coder_b: T | None
    coder_c: T | None
    model: T | None


@dataclass(frozen=True)
class ReplacementPanelResult:
    alpha_abc: AlphaResult
    alpha_lbc: AlphaResult
    alpha_alc: AlphaResult
    alpha_abl: AlphaResult
    delta_a: float | None
    delta_b: float | None
    delta_c: float | None
    delta_min: float | None
    common_record_ids: tuple[str, ...]
    valid: bool
    undefined_reason: str | None


REPLACEMENT_STATISTIC_NAMES = (
    "alpha_ABC",
    "alpha_LBC",
    "alpha_ALC",
    "alpha_ABL",
    "delta_A",
    "delta_B",
    "delta_C",
    "delta_min",
)


def _difference(replacement: AlphaResult, human: AlphaResult) -> float | None:
    if not replacement.valid or not human.valid:
        return None
    assert replacement.alpha is not None and human.alpha is not None
    return replacement.alpha - human.alpha


def replacement_panel_analysis(
    panels: Iterable[DimensionPanel[T]], distance: Callable[[T, T], float]
) -> ReplacementPanelResult:
    """Calculate all four alphas on exactly one common complete-case sequence."""

    complete = tuple(
        panel
        for panel in panels
        if all(value is not None for value in (panel.coder_a, panel.coder_b, panel.coder_c, panel.model))
    )
    abc = krippendorff_alpha(
        ((p.coder_a, p.coder_b, p.coder_c) for p in complete), distance
    )
    lbc = krippendorff_alpha(
        ((p.model, p.coder_b, p.coder_c) for p in complete), distance
    )
    alc = krippendorff_alpha(
        ((p.coder_a, p.model, p.coder_c) for p in complete), distance
    )
    abl = krippendorff_alpha(
        ((p.coder_a, p.coder_b, p.model) for p in complete), distance
    )
    delta_a, delta_b, delta_c = (
        _difference(lbc, abc),
        _difference(alc, abc),
        _difference(abl, abc),
    )
    deltas = (delta_a, delta_b, delta_c)
    valid = all(result.valid for result in (abc, lbc, alc, abl))
    reason = None
    if not valid:
        invalid = [
            name + ":" + str(result.undefined_reason)
            for name, result in (("alpha_ABC", abc), ("alpha_LBC", lbc), ("alpha_ALC", alc), ("alpha_ABL", abl))
            if not result.valid
        ]
        reason = ";".join(invalid)
    return ReplacementPanelResult(
        alpha_abc=abc,
        alpha_lbc=lbc,
        alpha_alc=alc,
        alpha_abl=abl,
        delta_a=delta_a,
        delta_b=delta_b,
        delta_c=delta_c,
        delta_min=min(value for value in deltas if value is not None) if all(value is not None for value in deltas) else None,
        common_record_ids=tuple(panel.record_id for panel in complete),
        valid=valid,
        undefined_reason=reason,
    )


def replacement_statistic_values(
    panels: Iterable[DimensionPanel[T]], distance: Callable[[T, T], float]
) -> dict[str, StatisticValue]:
    """Joint evaluator suitable for one project-level bootstrap replicate."""

    result = replacement_panel_analysis(panels, distance)
    alpha_items = {
        "alpha_ABC": result.alpha_abc,
        "alpha_LBC": result.alpha_lbc,
        "alpha_ALC": result.alpha_alc,
        "alpha_ABL": result.alpha_abl,
    }
    values = {
        name: StatisticValue(item.alpha, item.valid, item.undefined_reason)
        for name, item in alpha_items.items()
    }
    delta_items = {
        "delta_A": result.delta_a,
        "delta_B": result.delta_b,
        "delta_C": result.delta_c,
        "delta_min": result.delta_min,
    }
    for name, value in delta_items.items():
        values[name] = StatisticValue(value, value is not None, None if value is not None else result.undefined_reason)
    return values
