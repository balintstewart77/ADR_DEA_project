"""Display-layer collection grouping for Dataset Demand views."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from dashboard.data.loader import (
    collection_labels_for_dataset,
    reference_collection_membership_rows,
)

COLLECTION_VIEW_GROUPED = "grouped"
COLLECTION_VIEW_INDIVIDUAL = "individual"


def normalise_collection_view(value: str | None) -> str:
    if value == COLLECTION_VIEW_INDIVIDUAL:
        return COLLECTION_VIEW_INDIVIDUAL
    return COLLECTION_VIEW_GROUPED


@lru_cache(maxsize=None)
def _collection_labels_cached(dataset: str) -> tuple[str, ...]:
    return tuple(collection_labels_for_dataset(dataset))


def collection_membership_reference_frame() -> pd.DataFrame:
    """Return the reference-defined collection membership used by the dashboard."""
    return pd.DataFrame(
        reference_collection_membership_rows(),
        columns=["collection", "product", "member"],
    )


def with_collection_display(df: pd.DataFrame, display_mode: str | None) -> pd.DataFrame:
    """Return dataset rows labelled either by collection or by individual dataset.

    Grouped mode collapses only rows whose canonical dataset matches a
    reference-defined linked product with a collection_label. Other datasets
    remain visible as individual dataset rows.
    """
    mode = normalise_collection_view(display_mode)
    if df.empty:
        return df.assign(
            display_dataset=pd.Series(dtype=object),
            display_kind=pd.Series(dtype=object),
            source_dataset=pd.Series(dtype=object),
            collection=pd.Series(dtype=object),
        )

    if mode == COLLECTION_VIEW_INDIVIDUAL:
        work = df.copy()
        work["display_dataset"] = work["dataset"]
        work["display_kind"] = "dataset"
        work["source_dataset"] = work["dataset"]
        work["collection"] = ""
        return work

    rows = []
    for record in df.to_dict("records"):
        dataset = str(record.get("dataset") or "")
        labels = _collection_labels_cached(dataset)
        if labels:
            for label in labels:
                rows.append({
                    **record,
                    "display_dataset": label,
                    "display_kind": "collection",
                    "source_dataset": dataset,
                    "collection": label,
                })
        else:
            rows.append({
                **record,
                "display_dataset": dataset,
                "display_kind": "dataset",
                "source_dataset": dataset,
                "collection": "",
            })
    return pd.DataFrame(rows)


def display_entity_counts(display_df: pd.DataFrame) -> pd.DataFrame:
    if display_df.empty:
        return pd.DataFrame(columns=["display_dataset", "display_kind", "Projects"])
    project_key = "Record ID" if "Record ID" in display_df.columns else "Project ID"
    return (
        display_df
        .drop_duplicates(subset=[project_key, "display_dataset"])
        .groupby(["display_dataset", "display_kind"], as_index=False)[project_key]
        .nunique()
        .rename(columns={project_key: "Projects"})
    )


def display_entity_exposure(
    display_df: pd.DataFrame,
    dataset_exposure: pd.DataFrame,
) -> pd.DataFrame:
    """Exposure lookup for current display entities.

    Dataset rows keep their dataset exposure. Collection rows use the earliest
    availability among visible reference-matched member rows, which is
    equivalent to the maximum exposure within the register window.
    """
    if display_df.empty:
        return pd.DataFrame(
            columns=["display_dataset", "exposure_years", "availability_basis"]
        ).set_index("display_dataset")

    joined = display_df[["display_dataset", "display_kind", "source_dataset"]].drop_duplicates()
    joined = joined.join(dataset_exposure, on="source_dataset")

    rows = []
    for display_dataset, group in joined.groupby("display_dataset", sort=False):
        kind = str(group["display_kind"].iloc[0])
        exposure = group["exposure_years"].dropna()
        if exposure.empty:
            exposure_years = pd.NA
        else:
            exposure_years = float(exposure.max())
        if kind == "collection":
            basis = "reference collection member availability"
        else:
            basis_values = group["availability_basis"].dropna().astype(str).unique()
            basis = basis_values[0] if len(basis_values) else ""
        rows.append({
            "display_dataset": display_dataset,
            "exposure_years": exposure_years,
            "availability_basis": basis,
        })
    return pd.DataFrame(rows).set_index("display_dataset")
