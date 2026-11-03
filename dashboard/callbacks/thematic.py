"""Thematic Analysis callbacks."""

from functools import lru_cache
from html import escape

import pandas as pd

from dash import ClientsideFunction, ctx, dcc, html, Input, Output, State, no_update

from dashboard.data.thematic import (
    THEMATIC_DATA_AVAILABLE,
    _split_semicolon_values,
    build_thematic_aggregates,
    domain_breadth_aggregates,
    df_thematic_projects,
)
from dashboard.dataset_normalisation import iter_dataset_entries
from dashboard.display_text import researcher_display_text
from dashboard.data.registry import PARTIAL_YEAR_INFO, df_all
from dashboard.data.filtering import (
    ENRICHED_FACETS,
    _get_enriched_register_display_df,
    _get_enriched_register_facet_options,
    _csv_date_stamp,
)
from dashboard.charts.template import CHART_HEIGHT, annotate_empty
from dashboard.charts.thematic import (
    make_thematic_trend, make_thematic_totals_bar, make_tag_domain_bar,
    make_cross_heatmap,
    make_domain_cooccurrence, make_latent_demand_cooccurrence,
    make_compact_distribution_bar,
    make_record_linkage_trend, make_domain_record_linkage_breakdown,
    make_domain_linkage_map,
    make_researcher_sector_cooccurrence, make_domain_breadth_trend,
)
from dashboard.components.data_grid import page_size_patch
from dashboard.config import DOMAIN_COLOURS, PURPOSE_COLOURS, TAG_COLOURS
from dashboard.layout.analysis.thematic import ENRICHED_PREVIEW_COLUMNS
from dashboard.data.uptake import SERVED_DOMAIN_PAIRS
from dashboard.data.year_filter import (
    YearRange,
    filter_records_by_year,
    filter_related_by_record_ids,
    parse_accreditation_dates,
    selected_record_ids,
    year_range,
)


_YEAR_RANGE = year_range(df_all)


_ENRICHED_DETAIL_COLUMNS = set(ENRICHED_PREVIEW_COLUMNS) | {"details_action"}
_PREVIEW_CHARACTER_LIMIT = 96
_PREVIEW_ENTRY_LIMIT = 2


def _enriched_text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _enriched_detail_control(record_id: str, label: str) -> str:
    safe_record_id = escape(record_id, quote=True)
    safe_label = escape(label, quote=True)
    return (
        '<button type="button" class="enriched-detail-trigger" '
        f'data-record-id="{safe_record_id}" '
        f'aria-label="{safe_label} for Record ID {safe_record_id}">{safe_label}</button>'
    )


def _escape_with_line_breaks(text: str) -> str:
    """Escape text for the markdown cell, keeping source line breaks (e.g. one
    researcher per line) as <br> instead of letting HTML collapse them."""
    lines = (line.strip() for line in text.splitlines())
    return "<br>".join(escape(line, quote=True) for line in lines if line)


def _generic_preview_display(value, record_id: str) -> str:
    """Render a character preview for fields without a reliable entry parser."""
    text = _enriched_text(value)
    if not text:
        return "—"
    if len(text) <= _PREVIEW_CHARACTER_LIMIT:
        return _escape_with_line_breaks(text)
    preview = _escape_with_line_breaks(text[:_PREVIEW_CHARACTER_LIMIT].rstrip() + "…")
    return (
        '<div class="enriched-preview">'
        f'<span class="enriched-preview-text">{preview}</span> '
        f'{_enriched_detail_control(record_id, "View full value")}'
        '</div>'
    )


def _entry_preview_display(entries: list[str], value, record_id: str) -> str:
    """Render parser-ordered entries without altering the parser's count semantics."""
    if not entries:
        return _generic_preview_display(value, record_id)
    shown = "; ".join(entries[:_PREVIEW_ENTRY_LIMIT])
    safe_shown = escape(shown, quote=True)
    remaining = len(entries) - _PREVIEW_ENTRY_LIMIT
    if remaining <= 0:
        return safe_shown
    return (
        '<div class="enriched-preview">'
        f'<span class="enriched-preview-text">{safe_shown}</span> '
        f'{_enriched_detail_control(record_id, f"+{remaining} more entries")}'
        '</div>'
    )


def _dataset_preview_display(value, record_id: str) -> str:
    entries = [part for _, _, part in (iter_dataset_entries(value) or [])]
    return _entry_preview_display(entries, value, record_id)


def _semicolon_preview_display(value, record_id: str) -> str:
    return _entry_preview_display(_split_semicolon_values(value), value, record_id)


def _enriched_detail_display_fields(record: dict) -> list:
    """Build a modal body from the full table values, not preview strings."""
    fields = [
        ("Project ID", record.get("Project ID")),
        ("Record ID", record.get("id")),
        ("Title", record.get("Title")),
        ("Researchers", researcher_display_text(record.get("Researchers"))),
        ("Datasets Used", record.get("Datasets Used")),
        ("Processing environment", record.get("Secure Research Service")),
        ("Accreditation Date", record.get("Accreditation Date")),
        ("Record Linkage", record.get("record_linkage")),
        ("Collection method", record.get("dataset_collection_methods")),
        ("Temporal structure", record.get("dataset_temporal_structures")),
        ("Unit of observation", record.get("dataset_units")),
        ("Researcher sector", record.get("researcher_sectors")),
        ("Domains", record.get("substantive_domains")),
        ("Substantive domain count", record.get("substantive_domain_count")),
        ("Purpose", record.get("analytical_purpose")),
        ("Cross-cutting tags", record.get("cross_cutting_tags")),
        ("Rationale", record.get("rationale")),
    ]
    return [
        html.Div([
            html.Dt(label),
            html.Dd(_enriched_text(value) or "—"),
        ])
        for label, value in fields
    ]


@lru_cache(maxsize=16)
def _cached_aggregates(selection_key: tuple) -> dict:
    record_ids = selected_record_ids(df_all, selection_key, _YEAR_RANGE)
    selected = filter_related_by_record_ids(df_thematic_projects, record_ids)
    aggregates = build_thematic_aggregates(selected)
    aggregates.update(domain_breadth_aggregates(
        df_all, df_thematic_projects, selection_key, _YEAR_RANGE,
    ))
    return aggregates


def _aggregates(selection) -> dict:
    return _cached_aggregates(tuple(selection or ()))


def _filter_enriched_accreditation_year_range(display, year_range, year_min, year_max):
    return filter_records_by_year(display, year_range, YearRange(int(year_min), int(year_max)))


def _rationale_display(rationale, title, record_id) -> str:
    """Return escaped, measurable details markup without changing source text."""
    if rationale is None or pd.isna(rationale) or not str(rationale).strip():
        return '<span class="rationale-short">—</span>'

    source = str(rationale)
    safe_rationale = escape(source, quote=True)
    label_target = str(title).strip() if title is not None else ""
    if not label_target:
        label_target = str(record_id).strip() or "this project"
    safe_target = escape(label_target, quote=True)
    safe_record_id = escape(str(record_id).strip(), quote=True)
    return (
        f'<div class="rationale-cell" data-record-id="{safe_record_id}">'
        f'<span class="rationale-preview">{safe_rationale}</span>'
        '<details class="rationale-details" data-overflow="unknown">'
        f'<summary aria-label="Toggle full model-generated rationale for {safe_target}">'
        '<span class="rationale-toggle">'
        '<span class="rationale-read-more">Read more</span>'
        '<span class="rationale-show-less">Show less</span>'
        '</span>'
        '</summary>'
        f'<div class="rationale-full">{safe_rationale}</div>'
        '</details>'
        '</div>'
    )


def _enriched_table_records(display) -> list[dict]:
    """Build Record-ID-keyed rows with full source values and display previews."""
    if "Record ID" not in display.columns:
        raise KeyError("Enriched Register table rows require Record ID")
    record_ids = display["Record ID"].astype("string").str.strip()
    if record_ids.isna().any() or record_ids.eq("").any() or record_ids.duplicated().any():
        raise ValueError("Enriched Register Record ID values must be unique and non-blank")

    records = []
    for row in display.to_dict("records"):
        record_id = str(row.pop("Record ID")).strip()
        row["id"] = record_id
        row["Title_display"] = _generic_preview_display(row.get("Title"), record_id)
        row["Researchers_display"] = _generic_preview_display(
            researcher_display_text(row.get("Researchers")), record_id,
        )
        row["Datasets Used_display"] = _dataset_preview_display(
            row.get("Datasets Used"), record_id,
        )
        row["Secure Research Service_display"] = _generic_preview_display(
            row.get("Secure Research Service"), record_id,
        )
        for display_column, source_column in ENRICHED_PREVIEW_COLUMNS.items():
            if display_column in row:
                continue
            row[display_column] = _semicolon_preview_display(
                row.get(source_column), record_id,
            )
        row["details_action"] = _enriched_detail_control(record_id, "View details")
        row["rationale_display"] = _rationale_display(
            row.get("rationale"), row.get("Title"), record_id,
        )
        records.append(row)
    return records


def _enriched_rows_with_iso_dates(display) -> list[dict]:
    """Table rows for a filtered display frame, with ISO accreditation dates."""
    display = display.copy()
    display["Accreditation Date"] = (
        parse_accreditation_dates(display).dt.strftime("%Y-%m-%d").fillna("")
    )
    return _enriched_table_records(display)


@lru_cache(maxsize=1)
def _enriched_records_by_id() -> dict[str, dict]:
    """Every Enriched Register row keyed by Record ID, for the detail modal.

    A row's values do not depend on the active filters, so the modal looks
    the record up here rather than uploading the whole table from the browser
    on every page change and cell click.
    """
    display, _ = _get_enriched_register_display_df(
        *_ALL_ENRICHED_FILTERS, include_record_id=True,
    )
    return {row["id"]: row for row in _enriched_rows_with_iso_dates(display)}


# One dropdown per facet, e.g. "domain_count" -> "enriched-domain-count-filter".
ENRICHED_FILTER_DROPDOWN_IDS = tuple(
    f"enriched-{facet.replace('_', '-')}-filter" for facet in ENRICHED_FACETS
)
# Search text plus one "ALL" per dropdown: the unfiltered register.
_ALL_ENRICHED_FILTERS = (None, *(["ALL"] * len(ENRICHED_FILTER_DROPDOWN_IDS)))


def register(app):
    if not THEMATIC_DATA_AVAILABLE:
        return

    @app.callback(
        Output("enriched-search", "value"),
        *[Output(dropdown_id, "value") for dropdown_id in ENRICHED_FILTER_DROPDOWN_IDS],
        Output("enriched-accreditation-year-filter", "value"),
        Output("enriched-register-table", "paginationGoTo"),
        Input("enriched-clear-filters-btn", "n_clicks"),
        State("enriched-accreditation-year-filter", "min"),
        State("enriched-accreditation-year-filter", "max"),
        prevent_initial_call=True,
    )
    def clear_enriched_filters(_n_clicks, year_min, year_max):
        # An empty dropdown means "ALL" to the filters and shows its "All …" placeholder.
        return ("", *[None] * len(ENRICHED_FILTER_DROPDOWN_IDS), [year_min, year_max], "first")

    @app.callback(
        Output("enriched-register-table", "dashGridOptions"),
        Input("enriched-page-size", "value"),
        prevent_initial_call=True,
    )
    def set_enriched_page_size(page_size):
        return page_size_patch(page_size)

    # A page, sort or data change collapses expanded rationales and, while a
    # record is open, reports the Record IDs now on the visible page.
    app.clientside_callback(
        ClientsideFunction(namespace="enrichedRegister", function_name="pageChanged"),
        Output("enriched-register-view", "data"),
        Input("enriched-register-table", "virtualRowData"),
        Input("enriched-register-table", "paginationInfo"),
        State("enriched-record-detail-record-id", "data"),
    )

    @app.callback(
        Output("enriched-record-detail-modal", "is_open"),
        Output("enriched-record-detail-body", "children"),
        Output("enriched-record-detail-record-id", "data"),
        Input("enriched-register-table", "cellClicked"),
        Input("enriched-record-detail-close", "n_clicks"),
        Input("enriched-register-view", "data"),
        State("enriched-record-detail-record-id", "data"),
        prevent_initial_call=True,
    )
    def update_enriched_record_detail(cell, _close_clicks, view, selected_record_id):
        """Open details by Record ID and close them when the row leaves the page."""
        trigger = ctx.triggered_id
        if trigger == "enriched-record-detail-close":
            return False, [], None

        if (
            trigger == "enriched-register-table"
            and cell
            and cell.get("colId") in _ENRICHED_DETAIL_COLUMNS
        ):
            record = _enriched_records_by_id().get(str(cell.get("rowId") or "").strip())
            if record is not None:
                return (
                    True,
                    html.Dl(
                        _enriched_detail_display_fields(record),
                        className="enriched-record-detail-fields",
                    ),
                    record["id"],
                )

        if (
            trigger == "enriched-register-view"
            and selected_record_id
            and selected_record_id not in (view or {}).get("recordIds", [])
        ):
            return False, [], None

        return no_update, no_update, no_update

    @app.callback(
        Output("thematic-domain-totals", "figure"),
        Output("thematic-purpose-totals", "figure"),
        Output("deterministic-researcher-sector-cooccurrence", "figure"),
        Output("deterministic-record-linkage-distribution", "figure"),
        Output("deterministic-collection-method-distribution", "figure"),
        Output("deterministic-temporal-structure-distribution", "figure"),
        Output("deterministic-unit-distribution", "figure"),
        Output("deterministic-researcher-sector-distribution", "figure"),
        Output("thematic-project-count", "children"),
        Output("thematic-tagged-summary", "children"),
        Output("thematic-latent-demand-summary", "children"),
        Input("main-tabs", "active_tab"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_static_thematic_figures(_active_tab, year_selection):
        data = _aggregates(year_selection)
        empty = data["THEMATIC_PROJECT_COUNT"] == 0
        domain_totals = make_thematic_totals_bar(
            data["df_thematic_a_totals"], "domain", DOMAIN_COLOURS,
            "Projects by Domain", height=440,
        )
        purpose_totals = make_thematic_totals_bar(
            data["df_thematic_c_totals"], "purpose", PURPOSE_COLOURS,
            "Projects by Purpose", height=380,
        )

        researcher_sector_cooccurrence = make_researcher_sector_cooccurrence(
            data["df_researcher_sector_cooccurrence"],
            excluded_count=data["RESEARCHER_SECTOR_EXCLUDED_COUNT"],
        )
        record_linkage_distribution = make_compact_distribution_bar(
            data["df_record_linkage_totals"],
            "record_linkage",
            "Record Linkage",
            height=280,
        )
        collection_method_distribution = make_compact_distribution_bar(
            data["df_collection_method_totals"],
            "collection_method",
            "Collection method",
            multi_count=True,
            height=280,
        )
        temporal_structure_distribution = make_compact_distribution_bar(
            data["df_temporal_structure_totals"],
            "temporal_structure",
            "Temporal structure",
            multi_count=True,
            height=280,
        )
        unit_distribution = make_compact_distribution_bar(
            data["df_unit_totals"],
            "unit_of_observation",
            "Unit of observation",
            multi_count=True,
            height=280,
        )
        researcher_sector_distribution = make_compact_distribution_bar(
            data["df_researcher_sector_totals"],
            "researcher_sector",
            "Researcher sector",
            multi_count=True,
            height=280,
        )

        figures = (
            domain_totals, purpose_totals, researcher_sector_cooccurrence,
            record_linkage_distribution, collection_method_distribution,
            temporal_structure_distribution, unit_distribution,
            researcher_sector_distribution,
        )
        tagged_summary = (
            f"At least one tag applies to {data['THEMATIC_TAGGED_COUNT']:,} of "
            f"{data['THEMATIC_PROJECT_COUNT']:,} selected classified projects."
        )
        latent_summary = (
            f"Domain co-occurrence is computed over the "
            f"{data['LATENT_NO_LINKAGE_COUNT']:,} selected classified projects "
            "with no record linkage."
        )
        return (
            *(annotate_empty(fig, empty) for fig in figures),
            f"{data['THEMATIC_PROJECT_COUNT']:,}",
            tagged_summary,
            latent_summary,
        )

    def metric_col(metric_mode):
        return "pct_of_projects" if (metric_mode or "pct") == "pct" else "count"

    # Tag-by-domain bars have independent per-figure metric controls
    # (count vs % of the domain's classified projects).
    @app.callback(
        Output("thematic-covid-tag-domain", "figure"),
        Input("thematic-covid-tag-domain-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_covid_tag_domain(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_tag_domain_bar(
            data["df_thematic_covid_tag_by_domain"], DOMAIN_COLOURS,
            "COVID-19 & Pandemic by domain",
            metric=metric or "count",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("thematic-demographic-tag-domain", "figure"),
        Input("thematic-demographic-tag-domain-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_demographic_tag_domain(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_tag_domain_bar(
            data["df_thematic_demographic_tag_by_domain"], DOMAIN_COLOURS,
            "Demographic disparities by domain",
            metric=metric or "count",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("thematic-domain-trend", "figure"),
        Input("thematic-domain-trend-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_domain_trend(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_thematic_trend(
            data["df_thematic_a"], "domain", DOMAIN_COLOURS, metric_col(metric),
            "Substantive Domains Over Time",
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("thematic-purpose-trend", "figure"),
        Input("thematic-purpose-trend-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_purpose_trend(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_thematic_trend(
            data["df_thematic_c"], "purpose", PURPOSE_COLOURS, metric_col(metric),
            "Analytical Purpose Over Time",
            height=CHART_HEIGHT,
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("thematic-cross-domain-purpose", "figure"),
        Input("thematic-cross-domain-purpose-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_cross_domain_purpose(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_cross_heatmap(
            data["df_cross_domain_purpose"], "domain",
            "Substantive Domain × Analytical Purpose",
            colorscale=[[0, "#fef0ec"], [0.5, "#f4a582"], [1, "#d73027"]],
            height=560,
            metric=metric or "pct",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("thematic-tag-trend", "figure"),
        Input("thematic-tag-trend-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_tag_trend(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_thematic_trend(
            data["df_thematic_tag_by_year"], "tag", TAG_COLOURS, metric_col(metric),
            "Cross-Cutting Tags Over Time",
            height=CHART_HEIGHT,
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("thematic-domain-cooccurrence", "figure"),
        Input("thematic-domain-cooccurrence-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_domain_cooccurrence(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_domain_cooccurrence(
            data["df_domain_cooccurrence"],
            metric=metric or "pct",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("thematic-domain-breadth-trend", "figure"),
        Output("thematic-domain-breadth-coverage-warning", "children"),
        Input("thematic-domain-breadth-metric", "value"),
        Input("thematic-domain-breadth-granularity", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_domain_breadth_trend(metric, granularity, year_selection):
        data = _aggregates(year_selection)
        selected_granularity = granularity or "year"
        source = (
            data["df_domain_breadth_by_quarter"]
            if selected_granularity == "quarter"
            else data["df_domain_breadth_by_year"]
        )
        selection_coverage = data["domain_breadth_selection_coverage"]
        notes = []
        coverage_labels = (
            ("unmatched_classification", "unmatched record", "unmatched records"),
            ("missing_classification", "record with a missing classification", "records with missing classifications"),
            ("invalid_classification", "record with an invalid domain label", "records with invalid domain labels"),
        )
        coverage_notes = []
        for field, singular, plural in coverage_labels:
            count = int(selection_coverage[field])
            if count:
                coverage_notes.append(f"{count:,} {singular if count == 1 else plural}")
        if coverage_notes:
            notes.append(f"Classification coverage: {'; '.join(coverage_notes)}.")
        undated_selected = int(selection_coverage["undated_selected_records"])
        if undated_selected:
            record_label = "record" if undated_selected == 1 else "records"
            notes.append(
                f"{undated_selected:,} selected {record_label} have no usable accreditation date "
                "and are not shown in the trend."
            )
        if selection_coverage["undated_omitted_records"]:
            undated_omitted = int(selection_coverage["undated_omitted_records"])
            record_label = "record" if undated_omitted == 1 else "records"
            verb = "is" if undated_omitted == 1 else "are"
            notes.append(
                f"{undated_omitted:,} undated {record_label} {verb} omitted "
                "by the restricted year selection."
            )
        return (
            make_domain_breadth_trend(
                source,
                metric=metric or "pct",
                granularity=selected_granularity,
                partial_year_info=PARTIAL_YEAR_INFO,
                unclear_only_substantive_domains=(
                    selection_coverage["unclear_only_substantive_domains"]
                ),
                explicit_empty_substantive_domains=(
                    selection_coverage["explicit_empty_substantive_domains"]
                ),
            ),
            " ".join(notes),
        )

    @app.callback(
        Output("thematic-latent-demand", "figure"),
        Input("thematic-latent-demand-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_latent_demand(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_latent_demand_cooccurrence(
            data["df_latent_demand_cooccurrence"],
            SERVED_DOMAIN_PAIRS,
            metric=metric or "pct",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("deterministic-record-linkage-trend", "figure"),
        Input("deterministic-record-linkage-trend-metric", "value"),
        Input("deterministic-record-linkage-trend-view", "value"),
        Input("deterministic-record-linkage-trend-granularity", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_record_linkage_trend(metric, view, granularity, year_selection):
        data = _aggregates(year_selection)
        selected_granularity = granularity or "year"
        source = (
            data["df_record_linkage_by_quarter"]
            if selected_granularity == "quarter"
            else data["df_record_linkage_by_year"]
        )
        fig = make_record_linkage_trend(
            source,
            metric=metric or "pct",
            granularity=selected_granularity,
            partial_year_info=PARTIAL_YEAR_INFO,
            view=view or "any",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("deterministic-domain-linkage-map", "figure"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_domain_linkage_map(year_selection):
        data = _aggregates(year_selection)
        fig = make_domain_linkage_map(data["df_record_linkage_domain_pairs"])
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    _MULTI_COUNT_NOTE = "Multi-count: a project carrying both values counts in both lines."

    def _facet_trend_figure(df_by_year, category_col, colours, metric, title):
        fig = make_thematic_trend(
            df_by_year, category_col, colours, metric_col(metric), title,
            height=CHART_HEIGHT,
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        fig.add_annotation(
            text=_MULTI_COUNT_NOTE,
            xref="paper", yref="paper",
            x=0, y=1.07, showarrow=False,
            xanchor="left", yanchor="bottom",
            font=dict(size=10, color="#7f8c8d"),
        )
        return fig

    @app.callback(
        Output("deterministic-collection-method-trend", "figure"),
        Input("deterministic-collection-method-trend-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_collection_method_trend(metric, year_selection):
        data = _aggregates(year_selection)
        fig = _facet_trend_figure(
            data["df_collection_method_by_year"],
            "collection_method",
            {"Survey": "#e76f51", "Administrative": "#2a9d8f"},
            metric,
            "Collection Method Over Time",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("deterministic-temporal-structure-trend", "figure"),
        Input("deterministic-temporal-structure-trend-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_temporal_structure_trend(metric, year_selection):
        data = _aggregates(year_selection)
        fig = _facet_trend_figure(
            data["df_temporal_structure_by_year"],
            "temporal_structure",
            {"Cross-sectional": "#f4a261", "Longitudinal": "#6a3d9a"},
            metric,
            "Temporal Structure Over Time",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("deterministic-unit-trend", "figure"),
        Input("deterministic-unit-trend-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_unit_trend(metric, year_selection):
        data = _aggregates(year_selection)
        fig = _facet_trend_figure(
            data["df_unit_by_year"],
            "unit_of_observation",
            {
                "Individual": "#2a9d8f",
                "Household": "#e9c46a",
                "Business": "#264653",
                "Area": "#e76f51",
            },
            metric,
            "Unit of Observation Over Time",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("deterministic-domain-linkage-breakdown", "figure"),
        Input("deterministic-domain-linkage-metric", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_domain_linkage_breakdown(metric, year_selection):
        data = _aggregates(year_selection)
        fig = make_domain_record_linkage_breakdown(
            data["df_domain_record_linkage"],
            metric=metric or "pct",
        )
        return annotate_empty(fig, data["THEMATIC_PROJECT_COUNT"] == 0)

    @app.callback(
        Output("enriched-register-table", "rowData"),
        Output("enriched-browse-count", "children"),
        *[Output(dropdown_id, "options") for dropdown_id in ENRICHED_FILTER_DROPDOWN_IDS],
        Input("enriched-search", "value"),
        *[Input(dropdown_id, "value") for dropdown_id in ENRICHED_FILTER_DROPDOWN_IDS],
        Input("enriched-accreditation-year-filter", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
        State("enriched-accreditation-year-filter", "min"),
        State("enriched-accreditation-year-filter", "max"),
    )
    def update_enriched_register(
        search,
        dataset_filter,
        provider_filter,
        institution_filter,
        tre_filter,
        domain_filter,
        domain_count_filter,
        purpose_filter,
        tag_filter,
        record_linkage_filter,
        collection_method_filter,
        temporal_structure_filter,
        unit_filter,
        researcher_sector_filter,
        accreditation_year_range,
        portfolio_year_range,
        accreditation_year_min,
        accreditation_year_max,
    ):
        eligible_ids = selected_record_ids(df_all, portfolio_year_range, _YEAR_RANGE)
        display, _ = _get_enriched_register_display_df(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
            domain_filter,
            domain_count_filter,
            purpose_filter,
            tag_filter,
            record_linkage_filter,
            collection_method_filter,
            temporal_structure_filter,
            unit_filter,
            researcher_sector_filter,
            eligible_ids,
            include_record_id=True,
        )

        display = _filter_enriched_accreditation_year_range(
            display, accreditation_year_range, accreditation_year_min, accreditation_year_max,
        )
        count_text = (
            f"Showing {len(display):,} accreditation "
            f"record{'s' if len(display) != 1 else ''}"
        )

        records = _enriched_rows_with_iso_dates(display)
        facet_options = _get_enriched_register_facet_options(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
            domain_filter,
            domain_count_filter,
            purpose_filter,
            tag_filter,
            record_linkage_filter,
            collection_method_filter,
            temporal_structure_filter,
            unit_filter,
            researcher_sector_filter,
            eligible_ids,
            accreditation_year_range,
            accreditation_year_min,
            accreditation_year_max,
        )
        return (
            records,
            count_text,
            *(facet_options[facet] for facet in ENRICHED_FACETS),
        )

    @app.callback(
        Output("enriched-download-csv", "data"),
        Input("enriched-download-btn", "n_clicks"),
        State("enriched-search", "value"),
        *[State(dropdown_id, "value") for dropdown_id in ENRICHED_FILTER_DROPDOWN_IDS],
        State("enriched-accreditation-year-filter", "value"),
        State("enriched-accreditation-year-filter", "min"),
        State("enriched-accreditation-year-filter", "max"),
        State("portfolio-accreditation-year-filter", "value"),
        prevent_initial_call=True,
    )
    def download_enriched_csv(
        n_clicks,
        search,
        dataset_filter,
        provider_filter,
        institution_filter,
        tre_filter,
        domain_filter,
        domain_count_filter,
        purpose_filter,
        tag_filter,
        record_linkage_filter,
        collection_method_filter,
        temporal_structure_filter,
        unit_filter,
        researcher_sector_filter,
        accreditation_year_range,
        accreditation_year_min,
        accreditation_year_max,
        portfolio_year_range,
    ):
        eligible_ids = selected_record_ids(df_all, portfolio_year_range, _YEAR_RANGE)
        display, _ = _get_enriched_register_display_df(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
            domain_filter,
            domain_count_filter,
            purpose_filter,
            tag_filter,
            record_linkage_filter,
            collection_method_filter,
            temporal_structure_filter,
            unit_filter,
            researcher_sector_filter,
            eligible_ids,
        )
        filename = f"dea-enriched-register-{_csv_date_stamp()}.csv"
        display = _filter_enriched_accreditation_year_range(
            display, accreditation_year_range, accreditation_year_min, accreditation_year_max,
        )
        return dcc.send_data_frame(display.to_csv, filename, index=False)
