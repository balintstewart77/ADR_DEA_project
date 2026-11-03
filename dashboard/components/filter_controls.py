"""Shared helpers for filter dropdowns."""


def all_option_label(options: list[dict]) -> str:
    """Label of an option list's "ALL" reset entry, used as the placeholder.

    Filter dropdowns start empty and are clearable, so the placeholder is what
    an unfiltered dropdown shows. Filtering treats an empty value as "ALL".
    """
    return next(option["label"] for option in options if option["value"] == "ALL")


def label_with_count(label: str, count: int) -> str:
    """Option label carrying its project count, e.g. "Health  (12 projects)"."""
    return f"{label}  ({count} {'project' if count == 1 else 'projects'})"
