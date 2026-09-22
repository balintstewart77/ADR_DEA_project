"""Display-only tidying of multi-line register text.

These helpers change how researcher and dataset text is shown in tables. The
stored register values, parsing, filters and CSV exports are untouched.
"""

import re

from dashboard.dataset_normalisation import (
    iter_dataset_entries,
    normalise_dataset_name,
    normalise_provider_name,
)


# A line ending in a connective is an organisation name that wrapped.
_OPEN_TAIL_RE = re.compile(r"\b(?:of|and|for|the)$", re.IGNORECASE)


def _text_lines(value) -> list[str]:
    if value is None or not isinstance(value, str):
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


def researcher_display_text(value) -> str:
    """One researcher per line, rejoining lines the register wrapped.

    Conservative on purpose: only joins that are unambiguous, so a missed join
    leaves the source text as written rather than inventing a pairing.

    - "Daniele Cox," followed by a line with no comma (a lone organisation)
      becomes "Daniele Cox, Office for National Statistics".
    - A line starting with a lowercase word ("and Tropical Medicine"), or
      following a line that ends mid-name ("London School of"), continues
      the line before it.
    """
    lines = _text_lines(value)
    if not lines:
        return value if isinstance(value, str) else ""
    shown: list[str] = []
    pending_name = False
    for line in lines:
        if shown and pending_name and "," not in line:
            shown[-1] = f"{shown[-1]} {line}"
        elif shown and (line[0].islower() or _OPEN_TAIL_RE.search(shown[-1])):
            shown[-1] = f"{shown[-1]} {line}"
        else:
            shown.append(line)
        # A lone "Name," (no other comma) is waiting for its organisation.
        pending_name = shown[-1].endswith(",") and "," not in shown[-1][:-1]
    return "\n".join(shown)


def datasets_display_text(value) -> str:
    """Datasets grouped under their source organisation, one per line.

    Uses the shared dataset parser and the dashboard's standardised names,
    the same labels as the Dataset filter, so stray fragments in the source
    (for example "Data given for all available years unless otherwise
    stated.") are not shown. Falls back to the text as written when nothing
    parses.
    """
    groups: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for _line, provider, dataset in iter_dataset_entries(value) or []:
        organisation = normalise_provider_name(provider) if provider.strip() else ""
        dataset = normalise_dataset_name(dataset) or dataset
        key = (organisation, dataset.casefold())
        if key in seen:
            continue
        seen.add(key)
        groups.setdefault(organisation, []).append(dataset)
    if not groups:
        return value if isinstance(value, str) else ""
    blocks = []
    for organisation, datasets in groups.items():
        items = "\n".join(f"• {dataset}" for dataset in datasets)
        blocks.append(f"{organisation}\n{items}" if organisation else items)
    return "\n".join(blocks)
