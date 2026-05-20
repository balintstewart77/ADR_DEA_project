"""Thematic analysis data loading and filter option building."""

import os

import pandas as pd

from dashboard.config import THEMATIC_DIR, _PROJECT_ID_KEY_COL
from dashboard.data.keys import _project_id_key


def _filter_label_with_count(label: str, count: int) -> str:
    return f"{label}  ({count} {'project' if count == 1 else 'projects'})"


def load_thematic_data(thematic_dir):
    """Returns (data_dict, available_flag)."""
    try:
        df_thematic_a = pd.read_csv(os.path.join(thematic_dir, "layer_a_by_year.csv"), encoding="utf-8-sig")
        df_thematic_b = pd.read_csv(os.path.join(thematic_dir, "layer_b_by_year.csv"), encoding="utf-8-sig")
        df_thematic_c = pd.read_csv(os.path.join(thematic_dir, "layer_c_by_year.csv"), encoding="utf-8-sig")
        df_thematic_a_totals = pd.read_csv(os.path.join(thematic_dir, "layer_a_totals.csv"), encoding="utf-8-sig")
        df_thematic_b_totals = pd.read_csv(os.path.join(thematic_dir, "layer_b_totals.csv"), encoding="utf-8-sig")
        df_thematic_c_totals = pd.read_csv(os.path.join(thematic_dir, "layer_c_totals.csv"), encoding="utf-8-sig")
        df_cross_mode_domain = pd.read_csv(os.path.join(thematic_dir, "cross_mode_domain.csv"), encoding="utf-8-sig")
        df_cross_domain_purpose = pd.read_csv(os.path.join(thematic_dir, "cross_domain_purpose.csv"), encoding="utf-8-sig")
        with open(os.path.join(thematic_dir, "layer_summary.txt"), "r", encoding="utf-8") as _f:
            thematic_narrative = _f.read()
        df_thematic_projects = pd.read_csv(
            os.path.join(thematic_dir, "layer_classifications.csv"), encoding="utf-8-sig",
        )
        thematic_project_count = len(df_thematic_projects)

        # Remap legacy "Multi-Domain Linkage" -> "Cross-Domain Linkage"
        _LINKAGE_REMAP = {"Multi-Domain Linkage": "Cross-Domain Linkage"}
        for _ldf in [df_thematic_b, df_thematic_b_totals]:
            if "linkage_mode" in _ldf.columns:
                _ldf["linkage_mode"] = _ldf["linkage_mode"].replace(_LINKAGE_REMAP)
        # Aggregate rows that now share the same key after remapping
        if "linkage_mode" in df_thematic_b.columns:
            df_thematic_b = df_thematic_b.groupby(["Year", "linkage_mode"], as_index=False).agg(
                {"count": "sum", "total": "first", "pct_of_projects": "sum"}
            )
        if "linkage_mode" in df_thematic_b_totals.columns:
            df_thematic_b_totals = df_thematic_b_totals.groupby("linkage_mode", as_index=False)["count"].sum()
            df_thematic_b_totals = df_thematic_b_totals.sort_values("count", ascending=False)
        df_thematic_projects["linkage_mode"] = df_thematic_projects["linkage_mode"].replace(_LINKAGE_REMAP)
        # Merge Multi-Domain column into Cross-Domain in cross-tab
        if "Multi-Domain Linkage" in df_cross_mode_domain.columns:
            if "Cross-Domain Linkage" not in df_cross_mode_domain.columns:
                df_cross_mode_domain = df_cross_mode_domain.rename(columns={"Multi-Domain Linkage": "Cross-Domain Linkage"})
            else:
                df_cross_mode_domain["Cross-Domain Linkage"] = (
                    df_cross_mode_domain["Cross-Domain Linkage"] + df_cross_mode_domain["Multi-Domain Linkage"]
                )
                df_cross_mode_domain = df_cross_mode_domain.drop(columns=["Multi-Domain Linkage"])

        # Apply project-id keying on df_thematic_projects
        if "Project ID" in df_thematic_projects.columns:
            df_thematic_projects[_PROJECT_ID_KEY_COL] = df_thematic_projects["Project ID"].apply(_project_id_key)

        # Build filter options for the thematic browse table
        _domain_project_counts = {}
        for domains in df_thematic_projects["substantive_domains"].dropna():
            for domain in {d.strip() for d in str(domains).split(";") if d.strip()}:
                _domain_project_counts[domain] = _domain_project_counts.get(domain, 0) + 1
        _all_domains = sorted({
            d.strip()
            for domains in df_thematic_projects["substantive_domains"].dropna()
            for d in domains.split(";")
            if d.strip()
        })
        _thematic_domain_options = (
            [{"label": "All domains", "value": "ALL"}]
            + [
                {"label": _filter_label_with_count(d, _domain_project_counts.get(d, 0)), "value": d}
                for d in _all_domains
            ]
        )
        _linkage_project_counts = df_thematic_projects["linkage_mode"].dropna().value_counts()
        _all_linkage = sorted(df_thematic_projects["linkage_mode"].dropna().unique())
        _thematic_linkage_options = (
            [{"label": "All linkage modes", "value": "ALL"}]
            + [
                {"label": _filter_label_with_count(m, int(_linkage_project_counts.get(m, 0))), "value": m}
                for m in _all_linkage
            ]
        )
        _purpose_project_counts = {}
        for purposes in df_thematic_projects["analytical_purpose"].dropna():
            for purpose in {p.strip() for p in str(purposes).split(";") if p.strip()}:
                _purpose_project_counts[purpose] = _purpose_project_counts.get(purpose, 0) + 1
        _all_purposes = sorted({
            p.strip()
            for purposes in df_thematic_projects["analytical_purpose"].dropna()
            for p in purposes.split(";")
            if p.strip()
        })
        _thematic_purpose_options = (
            [{"label": "All purposes", "value": "ALL"}]
            + [
                {"label": _filter_label_with_count(p, _purpose_project_counts.get(p, 0)), "value": p}
                for p in _all_purposes
            ]
        )

        return {
            "df_thematic_a": df_thematic_a,
            "df_thematic_b": df_thematic_b,
            "df_thematic_c": df_thematic_c,
            "df_thematic_a_totals": df_thematic_a_totals,
            "df_thematic_b_totals": df_thematic_b_totals,
            "df_thematic_c_totals": df_thematic_c_totals,
            "df_cross_mode_domain": df_cross_mode_domain,
            "df_cross_domain_purpose": df_cross_domain_purpose,
            "df_thematic_projects": df_thematic_projects,
            "THEMATIC_NARRATIVE": thematic_narrative,
            "THEMATIC_PROJECT_COUNT": thematic_project_count,
            "_THEMATIC_DOMAIN_OPTIONS": _thematic_domain_options,
            "_THEMATIC_LINKAGE_OPTIONS": _thematic_linkage_options,
            "_THEMATIC_PURPOSE_OPTIONS": _thematic_purpose_options,
        }, True
    except (FileNotFoundError, KeyError):
        return {
            "df_thematic_a": pd.DataFrame(),
            "df_thematic_b": pd.DataFrame(),
            "df_thematic_c": pd.DataFrame(),
            "df_thematic_a_totals": pd.DataFrame(),
            "df_thematic_b_totals": pd.DataFrame(),
            "df_thematic_c_totals": pd.DataFrame(),
            "df_cross_mode_domain": pd.DataFrame(),
            "df_cross_domain_purpose": pd.DataFrame(),
            "df_thematic_projects": pd.DataFrame(),
            "THEMATIC_NARRATIVE": "",
            "THEMATIC_PROJECT_COUNT": 0,
            "_THEMATIC_DOMAIN_OPTIONS": [],
            "_THEMATIC_LINKAGE_OPTIONS": [],
            "_THEMATIC_PURPOSE_OPTIONS": [],
        }, False


_thematic_data, THEMATIC_DATA_AVAILABLE = load_thematic_data(THEMATIC_DIR)

# Unpack for convenient module-level access
df_thematic_a = _thematic_data["df_thematic_a"]
df_thematic_b = _thematic_data["df_thematic_b"]
df_thematic_c = _thematic_data["df_thematic_c"]
df_thematic_a_totals = _thematic_data["df_thematic_a_totals"]
df_thematic_b_totals = _thematic_data["df_thematic_b_totals"]
df_thematic_c_totals = _thematic_data["df_thematic_c_totals"]
df_cross_mode_domain = _thematic_data["df_cross_mode_domain"]
df_cross_domain_purpose = _thematic_data["df_cross_domain_purpose"]
df_thematic_projects = _thematic_data["df_thematic_projects"]
THEMATIC_NARRATIVE = _thematic_data["THEMATIC_NARRATIVE"]
THEMATIC_PROJECT_COUNT = _thematic_data["THEMATIC_PROJECT_COUNT"]
_THEMATIC_DOMAIN_OPTIONS = _thematic_data["_THEMATIC_DOMAIN_OPTIONS"]
_THEMATIC_LINKAGE_OPTIONS = _thematic_data["_THEMATIC_LINKAGE_OPTIONS"]
_THEMATIC_PURPOSE_OPTIONS = _thematic_data["_THEMATIC_PURPOSE_OPTIONS"]
