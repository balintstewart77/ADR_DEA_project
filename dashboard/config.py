import json
import os
from collections import namedtuple

try:
    from dashboard.taxonomy import DOMAIN_LABELS, PURPOSE_LABELS, TAG_LABELS
except ModuleNotFoundError:
    from taxonomy import DOMAIN_LABELS, PURPOSE_LABELS, TAG_LABELS

_PACKAGE_DIR = os.path.dirname(__file__)

DATA_DIR = os.path.join(_PACKAGE_DIR, "..", "data")

COLLECTION_COLOURS = {
    "Data First":                       "#3366cc",
    "LEO":                              "#dc3912",
    "ECHILD":                           "#109618",
    "Growing up in England":            "#ff9900",
    "Wage and Employment Dynamics":     "#6a3d9a",
    "GRADE":                            "#0099c6",
    "Agricultural Research Collection": "#e377c2",
}

PRIMARY_BAR = "#2a9d8f"
SECONDARY_BAR = "#e76f51"

# The active label *set* comes from the taxonomy dictionary (single source of
# truth); these overrides only assign a curated colour to each label. Labels
# introduced by a future ontology revision fall back to a palette colour rather
# than silently rendering grey, so the charts can never quietly lose a category.
_FALLBACK_PALETTE = [
    "#2a9d8f", "#264653", "#e9c46a", "#e76f51", "#6a3d9a", "#f4a261",
    "#1f77b4", "#ff7f0e", "#8c564b", "#2ca02c", "#9467bd", "#7f7f7f", "#bcbd22",
]


def _assign_colours(labels, overrides):
    palette = iter(_FALLBACK_PALETTE)
    return {label: (overrides.get(label) or next(palette, "#999999")) for label in labels}


_DOMAIN_COLOUR_OVERRIDES = {
    "Labour Market & Employment":           "#2a9d8f",
    "Business & Productivity":              "#264653",
    "Education & Skills":                   "#e9c46a",
    "Health & Social Care":                 "#e76f51",
    "Poverty, Wealth & Living Standards":   "#6a3d9a",
    "Migration & Demographics":             "#f4a261",
    "Crime & Justice":                      "#1f77b4",
    "Housing & Planning":                   "#8c564b",
    "Environment & Agriculture":            "#2ca02c",
    "Public Finance & Taxation":            "#9467bd",
    "Data Infrastructure & Methodology":    "#7f7f7f",
    "Unclear from Register Entry":          "#bcbd22",
}
DOMAIN_COLOURS = _assign_colours(DOMAIN_LABELS, _DOMAIN_COLOUR_OVERRIDES)

_PURPOSE_COLOUR_OVERRIDES = {
    "Descriptive Monitoring":                   "#3366cc",
    "Policy Evaluation / Impact Analysis":      "#dc3912",
    "Outcome Tracking":                         "#109618",
    "Life-Course / Trajectory Analysis":        "#6a3d9a",
    "Methodological / Infrastructure Research": "#0099c6",
    "Risk Prediction / Early Identification":   "#e377c2",
    "Service Interaction / Systems Analysis":   "#8c564b",
    "Unclear from Register Entry":              "#bdc3c7",
}
PURPOSE_COLOURS = _assign_colours(PURPOSE_LABELS, _PURPOSE_COLOUR_OVERRIDES)

_TAG_COLOUR_OVERRIDES = {
    "Demographic disparities / equity tag": "#d62728",
    "COVID-19 & Pandemic": "#ff7f0e",
}
TAG_COLOURS = _assign_colours(TAG_LABELS, _TAG_COLOUR_OVERRIDES)

FEEDBACK_EMAIL_URL = (
    "mailto:balintstewart@gmail.com"
    "?subject=Feedback%20on%20DEA%20Dashboard"
    "&body=Hello%20Balint%2C%0A%0AI%20have%20some%20feedback%20on%20the%20DEA%20dashboard%3A"
    "%0A%0AIssue%20%2F%20suggestion%3A"
    "%0APage%20%2F%20tab%3A"
    "%0AOptional%20screenshot%20or%20example%3A"
)
SOURCE_URL = "https://github.com/balintstewart77/ADR_DEA_project"

# Where the dashboard READS the frozen classification outputs (the results
# run). The pointers live in data/release_pointers.json so a register refresh
# can publish a new classification run without code changes; the defaults
# below apply when the file is missing or unreadable.
_PROJECT_ROOT = os.path.normpath(os.path.join(_PACKAGE_DIR, ".."))
_RELEASE_POINTERS_PATH = os.path.join(_PROJECT_ROOT, "data", "release_pointers.json")
_DEFAULT_RELEASE_POINTERS = {
    "classification_dir": "analysis/outputs_v4_8_rc2",
    "register_properties_csv": "analysis/outputs_deterministic_rc2/register_properties.csv",
}


def _load_release_pointers(path=_RELEASE_POINTERS_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        return {**_DEFAULT_RELEASE_POINTERS, **{
            key: value for key, value in loaded.items()
            if isinstance(value, str) and value.strip()
        }}
    except (OSError, ValueError):
        return dict(_DEFAULT_RELEASE_POINTERS)


_RELEASE_POINTERS = _load_release_pointers()
CLASSIFICATION_DIR = os.path.join(
    _PROJECT_ROOT, *_RELEASE_POINTERS["classification_dir"].split("/")
)
REGISTER_PROPERTIES_CSV = os.path.join(
    _PROJECT_ROOT, *_RELEASE_POINTERS["register_properties_csv"].split("/")
)
RUN_METADATA_JSON = os.path.join(CLASSIFICATION_DIR, "run_metadata.json")
_RELEASE_MODEL_FALLBACK = "see release metadata"


def _load_release_model(path=RUN_METADATA_JSON) -> str:
    """Model id recorded by the live classification run.

    Degrades to a placeholder when the metadata is missing or unreadable, so
    the displayed model can never silently drift from the run the release
    pointer targets (it either matches the run or visibly says it is unknown).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        model = str(metadata.get("model") or "").strip()
        return model or _RELEASE_MODEL_FALLBACK
    except (OSError, ValueError):
        return _RELEASE_MODEL_FALLBACK


RELEASE_MODEL = _load_release_model()
# Where register cleaning WRITES its duplicate-review diagnostic at startup.
# Kept separate from CLASSIFICATION_DIR so the live app never writes into the
# committed results directory.
CLEANING_OUTPUT_DIR = os.path.join(_PACKAGE_DIR, "..", "analysis", "outputs_v3")

REGISTER_SOURCE_ICON = "▣"
DERIVED_FIELD_ICON = "✦"
DERIVED_EMPTY_VALUE = "—"
SUBSTANTIVE_DOMAIN_COUNT_COL = "substantive_domain_count"
CROSS_CUTTING_TAGS_COL = "cross_cutting_tags"
RATIONALE_COL = "rationale"

# Columns whose presence defines a "classified" project (drive the classified
# mask). The cross-cutting tag is intentionally excluded: it is empty for most
# projects, so requiring it would wrongly drop them.
_DERIVED_CLASSIFICATION_COLUMNS = [
    "substantive_domains",
    "analytical_purpose",
]
_DERIVED_ENRICHMENT_COLUMNS = [
    SUBSTANTIVE_DOMAIN_COUNT_COL,
]
# Derived fields shown but not required for the classified mask.
_DERIVED_DISPLAY_ONLY_COLUMNS = [
    CROSS_CUTTING_TAGS_COL,
    RATIONALE_COL,
]
_ENRICHED_DERIVED_COLUMNS = [
    *_DERIVED_CLASSIFICATION_COLUMNS,
    *_DERIVED_ENRICHMENT_COLUMNS,
    *_DERIVED_DISPLAY_ONLY_COLUMNS,
]
_ENRICHED_REGISTER_DISPLAY_COLUMNS = [
    "Project ID",
    "Title",
    "Researchers",
    "Datasets Used",
    "Secure Research Service",
    "Accreditation Date",
    "record_linkage",
    "dataset_collection_methods",
    "dataset_temporal_structures",
    "dataset_units",
    "researcher_sectors",
    "substantive_domains",
    SUBSTANTIVE_DOMAIN_COUNT_COL,
    "analytical_purpose",
    CROSS_CUTTING_TAGS_COL,
    RATIONALE_COL,
]
_BROWSE_DISPLAY_COLUMNS = [
    "Project ID",
    "Title",
    "Researchers",
    "Datasets Used",
    "Secure Research Service",
    "Accreditation Date",
]
_PROJECT_ID_KEY_COL = "_project_id_key"
_MERGE_PROJECT_ID_KEY_COL = "_merge_project_id_key"
_MERGE_TITLE_KEY_COL = "_merge_title_key"

PartialYearInfo = namedtuple("PartialYearInfo", ["year", "label", "note"])
