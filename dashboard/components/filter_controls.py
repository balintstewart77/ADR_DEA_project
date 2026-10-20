"""Shared helpers for filter dropdowns."""


def all_option_label(options: list[dict]) -> str:
    """Label of an option list's "ALL" reset entry, used as the placeholder.

    Filter dropdowns start empty and are clearable, so the placeholder is what
    an unfiltered dropdown shows. Filtering treats an empty value as "ALL".
    """
    return next(option["label"] for option in options if option["value"] == "ALL")
