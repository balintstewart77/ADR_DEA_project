"""Visitor-facing dashboard date and provenance display checks."""

from collections.abc import Iterator
import re

from dashboard.data.registry import DATA_DATE, DATA_SOURCE_LABEL, PARTIAL_YEAR_INFO, df_all
from dashboard.layout.about import build_about_tab
from dashboard.layout.navbar import build_navbar


def _text_values(value) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _text_values(item)
    elif hasattr(value, "children"):
        yield from _text_values(value.children)


def test_public_coverage_date_is_computed_from_loaded_register_data():
    maximum = df_all["Accreditation Date"].max()
    assert DATA_DATE == maximum.strftime("%d %B %Y")
    assert PARTIAL_YEAR_INFO.note == (
        f"* {maximum.year} data covers Jan–{maximum.strftime('%b')} only"
    )


def test_public_provenance_uses_human_readable_source_not_internal_snapshot_path():
    navbar_text = " ".join(_text_values(build_navbar()))
    about_text = " ".join(_text_values(build_about_tab()))
    public_text = f"{navbar_text} {about_text}"

    assert DATA_SOURCE_LABEL in public_text
    assert DATA_DATE in public_text
    assert "register_snapshots/" not in public_text
    assert re.search(r"\b[0-9a-f]{64}\b", public_text, flags=re.IGNORECASE) is None
    assert "source file:" not in public_text.lower()
    assert "last updated" not in public_text.lower()


def test_footer_describes_data_coverage_using_the_loaded_data_date():
    from dashboard.app import app

    app_text = " ".join(_text_values(app.layout))
    assert f"Accreditation data through {DATA_DATE}" in app_text
    assert "last updated" not in app_text.lower()
