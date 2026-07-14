#!/usr/bin/env python3
"""Fetch and profile the public UK Areas of Research Interest API.

This is a read-only, exploratory snapshot. It does not match ARIs to DEA
projects and does not treat embedded UKRI links as evidence of answers or
policy influence.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests


API_URL = "https://ari.org.uk/api/questions"
DOCUMENTATION_URL = "https://help.overton.io/article/the-ari-org-uk-dataset/"
USER_AGENT = (
    "ADR-DEA-ARI-Exploration/1.0 "
    "(read-only government research dataset profiling; contact: repository maintainer)"
)
EXPECTED_TOP_LEVEL_FIELDS = {"data", "meta"}
DOCUMENTED_RECORD_FIELDS = [
    "questionId",
    "url",
    "question",
    "isArchived",
    "department",
    "questionGroup",
    "backgroundInformation",
    "publicationDate",
    "expiryDate",
    "contactDetails",
    "topics",
    "fieldsOfResearch",
    "tags",
    "relatedQuestions",
    "relatedUKRIProjects",
    "pageViewCount",
]
LIST_FIELDS = {
    "topics",
    "fieldsOfResearch",
    "tags",
    "relatedQuestions",
    "relatedUKRIProjects",
}
OVERLAP_DEPARTMENT_PATTERNS = (
    "department for education",
    "department for work and pensions",
    "ministry of justice",
    "hm revenue",
    "hmrc",
    "office for national statistics",
    "national statistics",
)
HEALTH_TERMS = re.compile(
    r"\b(health|nhs|disease|patient|clinical|medical|medicine|mental health|"
    r"public health|social care|epidemiolog|wellbeing|well-being)\b",
    re.IGNORECASE,
)


class FetchError(RuntimeError):
    """A retrieval or completeness failure with diagnostic context."""

    def __init__(self, message: str, diagnostic: dict[str, Any]):
        super().__init__(message)
        self.diagnostic = diagnostic


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=API_URL)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--pause-seconds", type=float, default=0.25)
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--read-timeout", type=float, default=45.0)
    parser.add_argument("--max-retries", type=int, default=4)
    return parser.parse_args()


def now_metadata() -> dict[str, str]:
    utc_now = datetime.now(timezone.utc)
    london_now = utc_now.astimezone(ZoneInfo("Europe/London"))
    return {
        "retrievedAtUtc": utc_now.isoformat(timespec="seconds"),
        "retrievedAtEuropeLondon": london_now.isoformat(timespec="seconds"),
        "retrievalDateEuropeLondon": london_now.strftime("%Y-%m-%d"),
        "filenameDate": london_now.strftime("%Y%m%d"),
    }


def request_json(
    session: requests.Session,
    url: str,
    *,
    timeout: tuple[float, float],
    max_retries: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, timeout=timeout)
            attempt_info: dict[str, Any] = {
                "attempt": attempt,
                "url": url,
                "statusCode": response.status_code,
                "contentType": response.headers.get("Content-Type"),
            }
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError as exc:
                    attempt_info["responseBodyPreview"] = response.text[:4000]
                    attempts.append(attempt_info)
                    raise FetchError(
                        f"API returned non-JSON content for {url}",
                        {"attempts": attempts, "exception": repr(exc)},
                    ) from exc
                if not isinstance(payload, dict):
                    attempt_info["responseBodyPreview"] = response.text[:4000]
                    attempts.append(attempt_info)
                    raise FetchError(
                        f"API returned a {type(payload).__name__}, expected an object",
                        {"attempts": attempts},
                    )
                attempt_info["responseBytes"] = len(response.content)
                attempts.append(attempt_info)
                return payload, attempt_info

            attempt_info["responseBodyPreview"] = response.text[:4000]
            attempts.append(attempt_info)
            retryable = response.status_code in {408, 425, 429, 500, 502, 503, 504}
            if not retryable or attempt == max_retries:
                raise FetchError(
                    f"API returned HTTP {response.status_code} for {url}",
                    {"attempts": attempts},
                )
            retry_after = response.headers.get("Retry-After", "")
            delay = float(retry_after) if retry_after.isdigit() else 1.5 * (2 ** (attempt - 1))
            time.sleep(delay)
        except requests.RequestException as exc:
            attempts.append({"attempt": attempt, "url": url, "exception": repr(exc)})
            if attempt == max_retries:
                raise FetchError(
                    f"Request failed after {max_retries} attempts for {url}",
                    {"attempts": attempts},
                ) from exc
            time.sleep(1.5 * (2 ** (attempt - 1)))
    raise AssertionError("retry loop exited unexpectedly")


def fetch_all_pages(args: argparse.Namespace, retrieval: dict[str, str]) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({"Accept": "application/json", "User-Agent": USER_AGENT})
    pages: list[dict[str, Any]] = []
    request_log: list[dict[str, Any]] = []
    visited_urls: set[str] = set()
    seen_page_numbers: set[int] = set()
    next_url: str | None = args.api_url
    expected_total: int | None = None
    expected_total_pages: int | None = None

    try:
        while next_url:
            if next_url in visited_urls:
                raise FetchError(
                    f"Pagination URL repeated: {next_url}",
                    {"requestLog": request_log, "visitedUrls": sorted(visited_urls)},
                )
            if pages:
                time.sleep(args.pause_seconds)
            payload, request_info = request_json(
                session,
                next_url,
                timeout=(args.connect_timeout, args.read_timeout),
                max_retries=args.max_retries,
            )
            request_log.append(request_info)
            visited_urls.add(next_url)

            if "data" not in payload or "meta" not in payload:
                raise FetchError(
                    "Response lacks required data/meta envelope",
                    {"url": next_url, "topLevelKeys": sorted(payload), "requestLog": request_log},
                )
            if not isinstance(payload["data"], list) or not isinstance(payload["meta"], dict):
                raise FetchError(
                    "Response data/meta types are invalid",
                    {
                        "url": next_url,
                        "dataType": type(payload["data"]).__name__,
                        "metaType": type(payload["meta"]).__name__,
                        "requestLog": request_log,
                    },
                )
            pagination = payload["meta"].get("pagination")
            if not isinstance(pagination, dict):
                raise FetchError(
                    "Response lacks meta.pagination object",
                    {"url": next_url, "meta": payload["meta"], "requestLog": request_log},
                )
            try:
                current_page = int(pagination["current_page"])
                page_total = int(pagination["total"])
                page_total_pages = int(pagination["total_pages"])
            except (KeyError, TypeError, ValueError) as exc:
                raise FetchError(
                    "Pagination metadata lacks numeric current_page/total/total_pages",
                    {"url": next_url, "pagination": pagination, "requestLog": request_log},
                ) from exc
            if current_page in seen_page_numbers:
                raise FetchError(
                    f"Pagination page {current_page} was returned more than once",
                    {"url": next_url, "requestLog": request_log},
                )
            if expected_total is None:
                expected_total = page_total
                expected_total_pages = page_total_pages
            elif page_total != expected_total or page_total_pages != expected_total_pages:
                raise FetchError(
                    "Pagination totals changed during retrieval; snapshot may have shifted",
                    {
                        "url": next_url,
                        "initialTotal": expected_total,
                        "pageTotal": page_total,
                        "initialTotalPages": expected_total_pages,
                        "pageTotalPages": page_total_pages,
                        "requestLog": request_log,
                    },
                )
            seen_page_numbers.add(current_page)
            pages.append(payload)

            links = pagination.get("links") or {}
            if not isinstance(links, dict):
                raise FetchError(
                    "meta.pagination.links is not an object",
                    {"url": next_url, "links": links, "requestLog": request_log},
                )
            next_value = links.get("next")
            if next_value is not None and not isinstance(next_value, str):
                raise FetchError(
                    "meta.pagination.links.next is not a string or null",
                    {"url": next_url, "next": next_value, "requestLog": request_log},
                )
            next_url = next_value or None
    finally:
        session.close()

    records = [record for page in pages for record in page["data"]]
    expected_pages = set(range(1, (expected_total_pages or 0) + 1))
    validation = {
        "metadataTotal": expected_total,
        "downloadedRecordCount": len(records),
        "metadataTotalPages": expected_total_pages,
        "downloadedPageCount": len(pages),
        "pageNumbers": sorted(seen_page_numbers),
        "uniquePageUrls": len(visited_urls),
        "recordCountMatchesMetadata": len(records) == expected_total,
        "allMetadataPagesRetrievedExactlyOnce": seen_page_numbers == expected_pages
        and len(visited_urls) == len(pages),
    }
    if not validation["recordCountMatchesMetadata"] or not validation[
        "allMetadataPagesRetrievedExactlyOnce"
    ]:
        raise FetchError(
            "Completeness validation failed; no complete profile will be created",
            {"validation": validation, "requestLog": request_log},
        )
    if any(not isinstance(record, dict) for record in records):
        raise FetchError(
            "One or more data entries are not objects",
            {"validation": validation, "requestLog": request_log},
        )

    return {
        "_retrieval": {
            **retrieval,
            "sourceUrl": args.api_url,
            "documentationUrl": DOCUMENTATION_URL,
            "userAgent": USER_AGENT,
            "pauseBetweenPagesSeconds": args.pause_seconds,
            "timeoutSeconds": {
                "connect": args.connect_timeout,
                "read": args.read_timeout,
            },
            "maxRetriesPerPage": args.max_retries,
            "requestLog": request_log,
            "validation": validation,
        },
        "pages": pages,
    }


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def stringify_csv(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def ordered_record_fields(records: list[dict[str, Any]]) -> list[str]:
    found = {field for record in records for field in record}
    return [field for field in DOCUMENTED_RECORD_FIELDS if field in found] + sorted(
        found - set(DOCUMENTED_RECORD_FIELDS)
    )


def write_flat_csv(path: Path, records: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for record in records:
            writer.writerow({field: stringify_csv(record.get(field)) for field in fields})


def parse_datetime(value: Any) -> datetime | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def percentile(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def fmt_number(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int) or float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.{digits}f}"


def fmt_pct(numerator: int, denominator: int) -> str:
    return "n/a" if not denominator else f"{100 * numerator / denominator:.1f}%"


def md_escape(value: Any) -> str:
    text = clean_text(value).replace("|", "\\|")
    return text or "(missing)"


def clipped(value: Any, limit: int = 180) -> str:
    text = clean_text(value)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> list[str]:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(md_escape(value) for value in row) + " |")
    return output


def schema_profile(records: list[dict[str, Any]], pages: list[dict[str, Any]]) -> dict[str, Any]:
    top_keys = sorted({key for page in pages for key in page})
    record_fields = sorted({key for record in records for key in record})
    record_field_rows = []
    for field in record_fields:
        present = sum(field in record for record in records)
        null_or_empty = sum(field in record and is_missing(record[field]) for record in records)
        types = Counter(type(record[field]).__name__ for record in records if field in record)
        record_field_rows.append(
            {
                "field": field,
                "present": present,
                "missingKey": len(records) - present,
                "nullOrEmpty": null_or_empty,
                "types": dict(sorted(types.items())),
            }
        )

    nested: dict[str, Any] = {}
    for field in ("relatedQuestions", "relatedUKRIProjects"):
        objects = [item for record in records for item in as_list(record.get(field))]
        object_items = [item for item in objects if isinstance(item, dict)]
        scalar_items = [item for item in objects if not isinstance(item, dict)]
        subfields = sorted({key for item in object_items for key in item})
        subfield_rows = []
        for subfield in subfields:
            present = sum(subfield in item for item in object_items)
            types = Counter(type(item[subfield]).__name__ for item in object_items if subfield in item)
            subfield_rows.append(
                {
                    "field": subfield,
                    "present": present,
                    "missingKey": len(object_items) - present,
                    "nullOrEmpty": sum(
                        subfield in item and is_missing(item[subfield]) for item in object_items
                    ),
                    "types": dict(sorted(types.items())),
                }
            )
        nested[field] = {
            "listItems": len(objects),
            "objectItems": len(object_items),
            "scalarItems": len(scalar_items),
            "subfields": subfield_rows,
            "example": object_items[0] if object_items else (scalar_items[0] if scalar_items else None),
        }
    return {
        "topLevelKeys": top_keys,
        "unexpectedTopLevelKeys": sorted(set(top_keys) - EXPECTED_TOP_LEVEL_FIELDS),
        "recordFields": record_field_rows,
        "unexpectedRecordFields": sorted(set(record_fields) - set(DOCUMENTED_RECORD_FIELDS)),
        "documentedFieldsNeverFound": sorted(set(DOCUMENTED_RECORD_FIELDS) - set(record_fields)),
        "nested": nested,
    }


def record_text(record: dict[str, Any], field: str) -> str:
    if field == "combinedText":
        return " ".join(
            part
            for part in (
                clean_text(record.get("questionGroup")),
                clean_text(record.get("backgroundInformation")),
                clean_text(record.get("question")),
            )
            if part
        )
    return clean_text(record.get(field))


def text_stats(records: list[dict[str, Any]], field: str) -> dict[str, Any]:
    texts = [record_text(record, field) for record in records]
    nonempty_lengths = [len(text) for text in texts if text]
    all_lengths = [len(text) for text in texts]
    return {
        "missing": sum(not text for text in texts),
        "minimum": min(nonempty_lengths) if nonempty_lengths else None,
        "q1": percentile(nonempty_lengths, 0.25),
        "median": percentile(nonempty_lengths, 0.5),
        "q3": percentile(nonempty_lengths, 0.75),
        "maximum": max(nonempty_lengths) if nonempty_lengths else None,
        "under50": sum(length < 50 for length in all_lengths),
        "under100": sum(length < 100 for length in all_lengths),
        "under250": sum(length < 250 for length in all_lengths),
    }


def normalised_question(value: Any, *, strip_numbering: bool = False) -> str:
    text = clean_text(value).casefold()
    if strip_numbering:
        text = re.sub(
            r"^(?:question\s+)?(?:[a-z]?\d+(?:[.\-]\d+)*[a-z]?\s*[.):\-]?|"
            r"[a-z]\s*[.):\-])\s+",
            "",
            text,
        )
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def duplicate_text_profile(records: list[dict[str, Any]]) -> dict[str, int]:
    exact = Counter(
        normalised_question(record.get("question"))
        for record in records
        if clean_text(record.get("question"))
    )
    stripped = Counter(
        normalised_question(record.get("question"), strip_numbering=True)
        for record in records
        if clean_text(record.get("question"))
    )
    exact_groups = [count for key, count in exact.items() if key and count > 1]
    stripped_groups = [count for key, count in stripped.items() if key and count > 1]
    return {
        "exactGroups": len(exact_groups),
        "exactRecords": sum(exact_groups),
        "exactExcess": sum(count - 1 for count in exact_groups),
        "numberInsensitiveGroups": len(stripped_groups),
        "numberInsensitiveRecords": sum(stripped_groups),
        "numberInsensitiveExcess": sum(count - 1 for count in stripped_groups),
    }


def list_values(record: dict[str, Any], field: str) -> list[str]:
    return [clean_text(value) for value in as_list(record.get(field)) if clean_text(value)]


def classification_profile(records: list[dict[str, Any]], field: str) -> dict[str, Any]:
    display_by_key: dict[str, str] = {}
    record_frequency: Counter[str] = Counter()
    raw_frequency: Counter[str] = Counter()
    raw_counts: list[int] = []
    unique_counts: list[int] = []
    noisy_examples = []
    useful_candidates = []
    for record in records:
        values = list_values(record, field)
        keys = [value.casefold() for value in values]
        for key, value in zip(keys, values):
            display_by_key.setdefault(key, value)
            raw_frequency[key] += 1
        unique_keys = list(dict.fromkeys(keys))
        record_frequency.update(unique_keys)
        raw_counts.append(len(values))
        unique_counts.append(len(unique_keys))
        duplicate_count = len(values) - len(unique_keys)
        if values and (duplicate_count or len(unique_keys) >= 12):
            noisy_examples.append(
                (
                    duplicate_count,
                    len(unique_keys),
                    str(record.get("questionId", "")),
                    clipped(record.get("question"), 110),
                    values,
                )
            )
        if 3 <= len(unique_keys) <= 8 and not duplicate_count:
            specificity = statistics.mean(len(key.split()) for key in unique_keys)
            useful_candidates.append(
                (
                    specificity,
                    str(record.get("questionId", "")),
                    clipped(record.get("question"), 110),
                    values,
                )
            )
    top = [
        {
            "value": display_by_key[key],
            "ariCount": count,
            "rawAssignments": raw_frequency[key],
        }
        for key, count in record_frequency.most_common(25)
    ]
    return {
        "missing": sum(not list_values(record, field) for record in records),
        "nonList": sum(record.get(field) is not None and not isinstance(record.get(field), list) for record in records),
        "medianRawAssigned": statistics.median(raw_counts),
        "medianUniqueAssigned": statistics.median(unique_counts),
        "recordsWithWithinListDuplicates": sum(raw > unique for raw, unique in zip(raw_counts, unique_counts)),
        "top": top,
        "noisyExamples": sorted(noisy_examples, reverse=True)[:3],
        "usefulExamples": sorted(useful_candidates, reverse=True)[:3],
    }


def link_distribution(counts: list[int]) -> list[tuple[int, int]]:
    return sorted(Counter(counts).items())


def grant_reference(project: dict[str, Any]) -> str:
    url = clean_text(project.get("url"))
    if not url:
        return ""
    return clean_text(parse_qs(urlparse(url).query).get("ref", [""])[0])


def is_clickable_url(value: Any) -> bool:
    parsed = urlparse(clean_text(value))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def ukri_project_key(project: dict[str, Any]) -> str:
    project_id = clean_text(project.get("projectId"))
    if project_id:
        return "id:" + project_id.casefold()
    reference = grant_reference(project)
    if reference:
        return "ref:" + reference.casefold()
    url = clean_text(project.get("url"))
    if url:
        return "url:" + url.casefold()
    return "fallback:" + "|".join(
        clean_text(project.get(field)).casefold()
        for field in ("title", "leadResearchOrganisation")
    )


def link_profile(records: list[dict[str, Any]]) -> dict[str, Any]:
    related_question_counts = [len(as_list(record.get("relatedQuestions"))) for record in records]
    ukri_counts = [len(as_list(record.get("relatedUKRIProjects"))) for record in records]
    linked_question_counts = [count for count in related_question_counts if count]
    linked_ukri_counts = [count for count in ukri_counts if count]

    projects_by_key: dict[str, dict[str, Any]] = {}
    ari_ids_by_project: defaultdict[str, set[str]] = defaultdict(set)
    link_occurrences: Counter[str] = Counter()
    project_objects: list[dict[str, Any]] = []
    for record in records:
        ari_id = str(record.get("questionId", ""))
        for item in as_list(record.get("relatedUKRIProjects")):
            if not isinstance(item, dict):
                continue
            key = ukri_project_key(item)
            projects_by_key.setdefault(key, item)
            ari_ids_by_project[key].add(ari_id)
            link_occurrences[key] += 1
            project_objects.append(item)

    shared = []
    for key, ari_ids in ari_ids_by_project.items():
        if len(ari_ids) > 1:
            project = projects_by_key[key]
            shared.append(
                {
                    "projectId": clean_text(project.get("projectId")),
                    "grantReference": grant_reference(project),
                    "title": clean_text(project.get("title")),
                    "ariCount": len(ari_ids),
                    "linkOccurrences": link_occurrences[key],
                    "exampleAriIds": sorted(ari_ids)[:5],
                }
            )
    shared.sort(key=lambda item: (-item["ariCount"], item["title"].casefold()))

    by_links = sorted(
        records,
        key=lambda record: (
            len(as_list(record.get("relatedUKRIProjects"))),
            str(record.get("questionId", "")),
        ),
    )
    none_examples = choose_diverse(
        [record for record in by_links if not as_list(record.get("relatedUKRIProjects"))], 5
    )
    few_examples = choose_diverse(
        [
            record
            for record in by_links
            if 1 <= len(as_list(record.get("relatedUKRIProjects"))) <= 2
        ],
        5,
    )
    maximum_links = max(ukri_counts, default=0)
    many_examples = choose_diverse(
        [
            record
            for record in records
            if len(as_list(record.get("relatedUKRIProjects"))) == maximum_links
        ],
        5,
    )
    unique_projects = len(projects_by_key)
    return {
        "relatedQuestionCounts": related_question_counts,
        "relatedQuestionDistribution": link_distribution(related_question_counts),
        "relatedQuestionLinked": len(linked_question_counts),
        "relatedQuestionMedianLinked": statistics.median(linked_question_counts)
        if linked_question_counts
        else None,
        "relatedQuestionMaximum": max(related_question_counts, default=0),
        "ukriCounts": ukri_counts,
        "ukriDistribution": link_distribution(ukri_counts),
        "ukriLinked": len(linked_ukri_counts),
        "ukriMedianLinked": statistics.median(linked_ukri_counts) if linked_ukri_counts else None,
        "ukriMaximum": max(ukri_counts, default=0),
        "embeddedProjectObjects": len(project_objects),
        "uniqueProjects": unique_projects,
        "projectIdPresent": sum(bool(clean_text(project.get("projectId"))) for project in project_objects),
        "grantReferenceExtractable": sum(bool(grant_reference(project)) for project in project_objects),
        "clickableUrlPresent": sum(is_clickable_url(project.get("url")) for project in project_objects),
        "sharedUniqueProjects": len(shared),
        "sharedLinkOccurrences": sum(item["linkOccurrences"] for item in shared),
        "sharedExamples": shared[:10],
        "noneExamples": none_examples,
        "fewExamples": few_examples,
        "manyExamples": many_examples,
    }


def is_overlap_department(record: dict[str, Any]) -> bool:
    department = clean_text(record.get("department")).casefold()
    return any(pattern in department for pattern in OVERLAP_DEPARTMENT_PATTERNS)


def is_health_related(record: dict[str, Any]) -> bool:
    searchable = " ".join(
        [
            clean_text(record.get("department")),
            clean_text(record.get("questionGroup")),
            clean_text(record.get("question")),
            " ".join(list_values(record, "topics")),
            " ".join(list_values(record, "tags")),
        ]
    )
    return bool(HEALTH_TERMS.search(searchable))


def choose_diverse(candidates: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    departments: Counter[str] = Counter()
    remaining = list(candidates)
    while remaining and len(chosen) < count:
        remaining.sort(
            key=lambda record: (
                departments[clean_text(record.get("department"))],
                str(record.get("questionId", "")),
            )
        )
        record = remaining.pop(0)
        chosen.append(record)
        departments[clean_text(record.get("department"))] += 1
    return chosen


def select_sample(records: list[dict[str, Any]], target: int = 30) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lengths = {id(record): len(record_text(record, "combinedText")) for record in records}
    ordered_lengths = sorted(lengths.values())
    short_cutoff = percentile(ordered_lengths, 0.10) or 0
    long_cutoff = percentile(ordered_lengths, 0.90) or 0
    linked_counts = [len(as_list(record.get("relatedUKRIProjects"))) for record in records]
    positive_link_counts = [count for count in linked_counts if count]
    many_cutoff = max(5, int(percentile(positive_link_counts, 0.75) or 5))

    def categories(record: dict[str, Any]) -> set[str]:
        ukri_count = len(as_list(record.get("relatedUKRIProjects")))
        result = {
            "archived" if bool(record.get("isArchived")) else "current",
            "background" if clean_text(record.get("backgroundInformation")) else "no_background",
        }
        if ukri_count == 0:
            result.add("ukri_zero")
        elif ukri_count <= 2:
            result.add("ukri_few")
        if ukri_count >= many_cutoff:
            result.add("ukri_many")
        if is_overlap_department(record):
            result.add("dea_overlap_department")
        if is_health_related(record):
            result.add("health_related")
        if lengths[id(record)] <= short_cutoff:
            result.add("short_text")
        if lengths[id(record)] >= long_cutoff:
            result.add("long_text")
        return result

    quotas = {
        "current": 5,
        "archived": 5,
        "background": 5,
        "no_background": 5,
        "ukri_zero": 5,
        "ukri_few": 5,
        "ukri_many": 5,
        "dea_overlap_department": 5,
        "health_related": 5,
        "short_text": 5,
        "long_text": 5,
    }
    category_map = {id(record): categories(record) for record in records}
    availability = Counter(category for values in category_map.values() for category in values)
    impossible = {category: quota for category, quota in quotas.items() if availability[category] < quota}
    if impossible:
        raise ValueError(f"Sample quotas cannot be met from live data: {impossible}")

    selected: list[dict[str, Any]] = []
    selected_ids: set[int] = set()
    selected_category_counts: Counter[str] = Counter()
    selected_departments: Counter[str] = Counter()
    while len(selected) < target:
        best: tuple[float, str, dict[str, Any]] | None = None
        for record in records:
            if id(record) in selected_ids:
                continue
            cats = category_map[id(record)]
            unmet_score = sum(
                100 + 15 * (quota - selected_category_counts[category])
                for category, quota in quotas.items()
                if category in cats and selected_category_counts[category] < quota
            )
            department = clean_text(record.get("department"))
            diversity_score = 35 if department and not selected_departments[department] else 0
            concentration_penalty = 4 * selected_departments[department]
            score = unmet_score + diversity_score - concentration_penalty
            candidate = (score, str(record.get("questionId", "")), record)
            if best is None or candidate[:2] > best[:2]:
                best = candidate
        if best is None:
            break
        record = best[2]
        selected.append(record)
        selected_ids.add(id(record))
        selected_category_counts.update(category_map[id(record)])
        selected_departments[clean_text(record.get("department"))] += 1

    unmet = {
        category: quota - selected_category_counts[category]
        for category, quota in quotas.items()
        if selected_category_counts[category] < quota
    }
    if len(selected) != target or unmet:
        raise ValueError(
            f"Could not construct {target}-row sample; selected={len(selected)}, unmet={unmet}"
        )

    reasons_by_id: dict[int, list[str]] = {}
    for record in selected:
        reasons = sorted(category_map[id(record)])
        department = clean_text(record.get("department"))
        if selected_departments[department] == 1:
            reasons.append("department_spread")
        reasons_by_id[id(record)] = reasons
    selected.sort(
        key=lambda record: (
            clean_text(record.get("department")).casefold(),
            bool(record.get("isArchived")),
            str(record.get("questionId", "")),
        )
    )
    return selected, {
        "target": target,
        "shortCutoff": short_cutoff,
        "longCutoff": long_cutoff,
        "manyUkriCutoff": many_cutoff,
        "categoryCounts": dict(selected_category_counts),
        "departmentCount": len(selected_departments),
        "reasonsByObjectId": reasons_by_id,
    }


def write_sample_csv(
    path: Path,
    sample: list[dict[str, Any]],
    sample_meta: dict[str, Any],
) -> None:
    fields = [
        "questionId",
        "url",
        "question",
        "isArchived",
        "department",
        "questionGroup",
        "publicationDate",
        "expiryDate",
        "backgroundInformation",
        "combinedTextLength",
        "topics",
        "fieldsOfResearch",
        "tags",
        "relatedQuestionsCount",
        "relatedUKRIProjectsCount",
        "selectionReasons",
    ]
    reasons = sample_meta["reasonsByObjectId"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in sample:
            writer.writerow(
                {
                    "questionId": stringify_csv(record.get("questionId")),
                    "url": stringify_csv(record.get("url")),
                    "question": stringify_csv(record.get("question")),
                    "isArchived": stringify_csv(record.get("isArchived")),
                    "department": stringify_csv(record.get("department")),
                    "questionGroup": stringify_csv(record.get("questionGroup")),
                    "publicationDate": stringify_csv(record.get("publicationDate")),
                    "expiryDate": stringify_csv(record.get("expiryDate")),
                    "backgroundInformation": stringify_csv(record.get("backgroundInformation")),
                    "combinedTextLength": len(record_text(record, "combinedText")),
                    "topics": stringify_csv(record.get("topics")),
                    "fieldsOfResearch": stringify_csv(record.get("fieldsOfResearch")),
                    "tags": stringify_csv(record.get("tags")),
                    "relatedQuestionsCount": len(as_list(record.get("relatedQuestions"))),
                    "relatedUKRIProjectsCount": len(as_list(record.get("relatedUKRIProjects"))),
                    "selectionReasons": "; ".join(reasons[id(record)]),
                }
            )


def examples_table(records: list[dict[str, Any]], link_field: str | None = None) -> list[list[Any]]:
    rows = []
    for record in records:
        rows.append(
            [
                record.get("questionId"),
                record.get("department"),
                len(as_list(record.get(link_field))) if link_field else len(record_text(record, "combinedText")),
                clipped(record.get("question"), 150),
            ]
        )
    return rows


def qualitative_examples(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    context_pattern = re.compile(
        r"^(and\b|what (?:is|are|does|do) (?:this|that|these|those|it|they|their)\b|"
        r"how (?:does|do|can|could|will|would) (?:this|that|these|those|it|they)\b)|"
        r"\b(above|this work|this area|these challenges|such approaches)\b",
        re.IGNORECASE,
    )
    intelligible = []
    dependent = []
    fragment = []
    broad = []
    for record in records:
        question = record_text(record, "question")
        background = record_text(record, "backgroundInformation")
        word_count = len(question.split())
        if 100 <= len(question) <= 400 and "?" in question and not context_pattern.search(question):
            intelligible.append(record)
        if context_pattern.search(question) or (0 < len(question) < 80 and len(background) >= 250):
            dependent.append(record)
        if question and "?" not in question and (word_count <= 14 or len(question) <= 90):
            fragment.append(record)
        if word_count <= 22 and re.search(
            r"\b(impact|impacts|role|future|opportunities|challenges|what works|how effective)\b",
            question,
            re.IGNORECASE,
        ):
            broad.append(record)

    intelligible.sort(key=lambda record: (abs(len(record_text(record, "question")) - 180), str(record.get("questionId"))))
    dependent.sort(
        key=lambda record: (
            -(len(record_text(record, "backgroundInformation")) - len(record_text(record, "question"))),
            str(record.get("questionId")),
        )
    )
    fragment.sort(key=lambda record: (len(record_text(record, "question")), str(record.get("questionId"))))
    broad.sort(key=lambda record: (len(record_text(record, "question")), str(record.get("questionId"))))
    return {
        "intelligible": choose_diverse(intelligible, 5),
        "dependent": choose_diverse(dependent, 5),
        "fragment": choose_diverse(fragment, 5),
        "broad": choose_diverse(broad, 5),
    }


def generate_report(
    raw: dict[str, Any],
    records: list[dict[str, Any]],
    sample: list[dict[str, Any]],
    sample_meta: dict[str, Any],
) -> str:
    retrieval = raw["_retrieval"]
    pages = raw["pages"]
    n = len(records)
    schema = schema_profile(records, pages)
    departments = Counter(clean_text(record.get("department")) for record in records)
    departments.pop("", None)
    groups = Counter(clean_text(record.get("questionGroup")) for record in records)
    groups.pop("", None)
    current_by_department: Counter[str] = Counter()
    archived_by_department: Counter[str] = Counter()
    for record in records:
        department = clean_text(record.get("department")) or "(missing)"
        if bool(record.get("isArchived")):
            archived_by_department[department] += 1
        else:
            current_by_department[department] += 1

    publication_dates = [parse_datetime(record.get("publicationDate")) for record in records]
    valid_publication_dates = [date for date in publication_dates if date is not None]
    year_department: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for record, date in zip(records, publication_dates):
        year = str(date.year) if date else "Missing"
        year_department[clean_text(record.get("department")) or "(missing)"][year] += 1
    years = sorted({year for counts in year_department.values() for year in counts}, key=lambda x: (x == "Missing", x))

    ids = [clean_text(record.get("questionId")) for record in records]
    duplicate_ids = {key: count for key, count in Counter(ids).items() if key and count > 1}
    duplicate_text = duplicate_text_profile(records)
    text_fields = ["question", "questionGroup", "backgroundInformation", "combinedText"]
    text_profiles = {field: text_stats(records, field) for field in text_fields}
    by_combined_length = sorted(
        [record for record in records if record_text(record, "combinedText")],
        key=lambda record: (len(record_text(record, "combinedText")), str(record.get("questionId", ""))),
    )
    shortest = by_combined_length[:10]
    longest = list(reversed(by_combined_length[-10:]))
    qualitative = qualitative_examples(records)
    classifications = {
        field: classification_profile(records, field)
        for field in ("topics", "fieldsOfResearch", "tags")
    }
    links = link_profile(records)

    missing_fields = {
        "department": sum(not clean_text(record.get("department")) for record in records),
        "publicationDate": sum(not clean_text(record.get("publicationDate")) for record in records),
        "expiryDate": sum(not clean_text(record.get("expiryDate")) for record in records),
        "questionGroup": sum(not clean_text(record.get("questionGroup")) for record in records),
        "backgroundInformation": sum(not clean_text(record.get("backgroundInformation")) for record in records),
    }
    invalid_publication_dates = sum(
        bool(clean_text(record.get("publicationDate"))) and parsed is None
        for record, parsed in zip(records, publication_dates)
    )

    lines = [
        "# UK Government Areas of Research Interest: exploratory profile",
        "",
        "> **Scope warning:** This is a descriptive profile, not an ARI-to-project matching evaluation. "
        "The ARI API's embedded Gateway to Research associations are described throughout as "
        "**existing system-generated related-project links**. They are not evidence that a project "
        "answered an ARI or influenced policy.",
        "",
        "## Live schema and retrieval checks",
        "",
        f"- API source: `{retrieval['sourceUrl']}`",
        f"- Documentation: `{retrieval['documentationUrl']}`",
        f"- Retrieved: {retrieval['retrievedAtUtc']} UTC ({retrieval['retrievedAtEuropeLondon']} Europe/London)",
        f"- Top-level response keys found: {', '.join(f'`{key}`' for key in schema['topLevelKeys'])}",
        f"- Unexpected top-level keys: {', '.join(f'`{key}`' for key in schema['unexpectedTopLevelKeys']) or 'none'}",
        f"- Pages retrieved: {len(pages):,}; metadata pages: {retrieval['validation']['metadataTotalPages']:,}; "
        f"page sequence: {retrieval['validation']['pageNumbers'][0]}–{retrieval['validation']['pageNumbers'][-1]}",
        f"- Records downloaded: {n:,}; metadata total: {retrieval['validation']['metadataTotal']:,}; "
        f"match: **{retrieval['validation']['recordCountMatchesMetadata']}**",
        f"- All metadata-listed pages retrieved exactly once: **{retrieval['validation']['allMetadataPagesRetrievedExactlyOnce']}**",
        "",
        "### Record fields",
        "",
    ]
    lines += markdown_table(
        ["Field", "Records containing key", "Key absent", "Null/empty", "Observed Python types"],
        (
            [
                item["field"],
                item["present"],
                item["missingKey"],
                item["nullOrEmpty"],
                json.dumps(item["types"], sort_keys=True),
            ]
            for item in schema["recordFields"]
        ),
    )
    absent_some = [item for item in schema["recordFields"] if item["missingKey"]]
    absent_some_description = ", ".join(
        f"`{item['field']}` ({item['missingKey']:,})" for item in absent_some
    )
    lines += [
        "",
        f"Fields absent from at least one record: {absent_some_description or 'none'}.",
        f"Unexpected relative to the documented record list: "
        f"{', '.join(f'`{field}`' for field in schema['unexpectedRecordFields']) or 'none'}.",
        f"Documented fields not found anywhere: "
        f"{', '.join(f'`{field}`' for field in schema['documentedFieldsNeverFound']) or 'none'}.",
        "",
        "### Nested link structures",
        "",
    ]
    for field in ("relatedQuestions", "relatedUKRIProjects"):
        nested = schema["nested"][field]
        lines += [
            f"**`{field}`:** {nested['listItems']:,} total list items; "
            f"{nested['objectItems']:,} objects and {nested['scalarItems']:,} scalar items.",
            "",
        ]
        lines += markdown_table(
            ["Subfield", "Objects containing key", "Key absent", "Null/empty", "Observed types"],
            (
                [
                    item["field"],
                    item["present"],
                    item["missingKey"],
                    item["nullOrEmpty"],
                    json.dumps(item["types"], sort_keys=True),
                ]
                for item in nested["subfields"]
            ),
        )
        lines += [
            "",
            "Example item (verbatim structure):",
            "",
            "```json",
            json.dumps(nested["example"], ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    lines += [
        "The live schema differs from the documentation in three visible ways: `postDate` and "
        "`dateUpdated` are additional record fields; dates include time components rather than only "
        "`YYYY-MM-DD`; and `relatedQuestions` contains objects with a `questionId` subfield rather "
        "than bare ID values. The raw snapshot preserves these structures unchanged.",
        "",
        "## A. Dataset overview",
        "",
        f"- Total ARIs: **{n:,}**",
        f"- Current: **{sum(not bool(record.get('isArchived')) for record in records):,}**; "
        f"archived: **{sum(bool(record.get('isArchived')) for record in records):,}**",
        f"- Publication dates: **{min(valid_publication_dates).date().isoformat() if valid_publication_dates else 'n/a'}** "
        f"to **{max(valid_publication_dates).date().isoformat() if valid_publication_dates else 'n/a'}**; "
        f"unparseable non-empty values: {invalid_publication_dates:,}",
        f"- Departments/agencies with non-empty names: **{len(departments):,}**",
        f"- Distinct non-empty question groups: **{len(groups):,}**",
        f"- Duplicate `questionId` values: **{len(duplicate_ids):,} groups / "
        f"{sum(duplicate_ids.values()):,} records**",
        f"- Exact duplicates after case/whitespace/punctuation normalisation: "
        f"**{duplicate_text['exactGroups']:,} groups / {duplicate_text['exactRecords']:,} records "
        f"({duplicate_text['exactExcess']:,} excess records)**",
        f"- Limited near-duplicate check after also removing a leading question number: "
        f"**{duplicate_text['numberInsensitiveGroups']:,} groups / "
        f"{duplicate_text['numberInsensitiveRecords']:,} records "
        f"({duplicate_text['numberInsensitiveExcess']:,} excess records)**",
        "",
        "The near-duplicate count is deliberately conservative and transparent; no pairwise fuzzy or "
        "semantic comparison was run.",
        "",
        "## B. Coverage",
        "",
        "### Counts by department",
        "",
    ]
    all_department_names = sorted(
        set(current_by_department) | set(archived_by_department),
        key=lambda department: (-(current_by_department[department] + archived_by_department[department]), department.casefold()),
    )
    lines += markdown_table(
        ["Department/agency", "Total", "Current", "Archived"],
        (
            [
                department,
                current_by_department[department] + archived_by_department[department],
                current_by_department[department],
                archived_by_department[department],
            ]
            for department in all_department_names
        ),
    )
    lines += [
        "",
        "### Counts by publication year and department",
        "",
    ]
    lines += markdown_table(
        ["Department/agency", *years, "Total"],
        (
            [department, *(year_department[department][year] for year in years), sum(year_department[department].values())]
            for department in all_department_names
        ),
    )
    lines += [
        "",
        "### Top question groups",
        "",
    ]
    lines += markdown_table(
        ["Question group", "ARIs"],
        ([group, count] for group, count in groups.most_common(25)),
    )
    sparse_departments = [
        (department, count)
        for department, count in sorted(departments.items(), key=lambda item: (item[1], item[0].casefold()))
        if count <= 5
    ]
    lines += [
        "",
        "### Sparse departments and missing coverage fields",
        "",
        "“Very few” is defined here as five or fewer records.",
        "",
    ]
    lines += markdown_table(["Department/agency", "ARIs"], sparse_departments or [["None", 0]])
    lines += [
        "",
    ]
    lines += markdown_table(
        ["Field", "Missing/empty", "Proportion"],
        ([field, count, fmt_pct(count, n)] for field, count in missing_fields.items()),
    )
    lines += [
        "",
        "## C. Text available for matching",
        "",
        "Length statistics are calculated on non-empty values. Threshold proportions use all ARIs, "
        "with missing text treated as zero characters. Combined text is the non-empty concatenation "
        "`questionGroup + backgroundInformation + question`.",
        "",
    ]
    lines += markdown_table(
        ["Field", "Missing", "Min", "Q1", "Median", "Q3", "Max", "<50", "<100", "<250"],
        (
            [
                field,
                f"{profile['missing']:,} ({fmt_pct(profile['missing'], n)})",
                fmt_number(profile["minimum"]),
                fmt_number(profile["q1"]),
                fmt_number(profile["median"]),
                fmt_number(profile["q3"]),
                fmt_number(profile["maximum"]),
                f"{profile['under50']:,} ({fmt_pct(profile['under50'], n)})",
                f"{profile['under100']:,} ({fmt_pct(profile['under100'], n)})",
                f"{profile['under250']:,} ({fmt_pct(profile['under250'], n)})",
            ]
            for field, profile in text_profiles.items()
        ),
    )
    lines += [
        "",
        "### Ten shortest combined usable texts",
        "",
    ]
    lines += markdown_table(
        ["ARI ID", "Department", "Characters", "Question"],
        examples_table(shortest),
    )
    lines += [
        "",
        "### Ten longest combined texts",
        "",
    ]
    lines += markdown_table(
        ["ARI ID", "Department", "Characters", "Question"],
        examples_table(longest),
    )
    lines += [
        "",
        "### Transparent qualitative spot checks",
        "",
        "These are rule-generated candidates, intended for human inspection rather than labels. "
        "“Intelligible alone” requires a 100–400 character question containing `?` and no explicit "
        "context-reference phrase. “Context-dependent” uses explicit references such as “this” or a "
        "question under 80 characters paired with at least 250 background characters. A fragment has "
        "no `?` and at most 14 words or 90 characters. A broad candidate has at most 22 words and a "
        "generic term such as impact, role, future, opportunities, challenges, or effectiveness.",
        "The 20 displayed candidates were manually spot-checked against their full group and "
        "background fields after generation. Borderline cases were retained to expose the limits of "
        "the rules: some short questions are intelligible alone but gain material scope from context.",
        "",
    ]
    qualitative_titles = {
        "intelligible": "Questions likely intelligible alone",
        "dependent": "Questions likely to depend on group/background context",
        "fragment": "Programme headings or fragments",
        "broad": "Unusually broad candidates",
    }
    for key, title in qualitative_titles.items():
        lines += [f"**{title}**", ""]
        lines += markdown_table(
            ["ARI ID", "Department", "Question"],
            (
                [record.get("questionId"), record.get("department"), clipped(record.get("question"), 220)]
                for record in qualitative[key]
            ),
        )
        lines.append("")

    lines += [
        "## D. Existing classifications",
        "",
        "Frequencies below count the number of ARIs containing each value after case-insensitive "
        "within-record deduplication; raw assignment counts expose repeated values inside arrays.",
        "",
    ]
    for field in ("topics", "fieldsOfResearch", "tags"):
        profile = classifications[field]
        lines += [
            f"### `{field}`",
            "",
            f"Missing/empty: **{profile['missing']:,} ({fmt_pct(profile['missing'], n)})**. "
            f"Median assigned per ARI: **{fmt_number(profile['medianRawAssigned'])} raw / "
            f"{fmt_number(profile['medianUniqueAssigned'])} unique**. Non-list values: "
            f"**{profile['nonList']:,}**. Records with within-list duplicates: "
            f"**{profile['recordsWithWithinListDuplicates']:,}**.",
            "",
        ]
        lines += markdown_table(
            ["Value", "ARIs", "Raw assignments"],
            ([item["value"], item["ariCount"], item["rawAssignments"]] for item in profile["top"]),
        )
        lines += ["", "Examples with broad/noisy assignment patterns:", ""]
        lines += markdown_table(
            ["ARI ID", "Duplicate assignments", "Unique values", "Question", "Values"],
            (
                [item[2], item[0], item[1], item[3], "; ".join(item[4])]
                for item in profile["noisyExamples"]
            ),
        )
        lines += ["", "Examples with compact, relatively specific values that may aid candidate retrieval:", ""]
        lines += markdown_table(
            ["ARI ID", "Question", "Values"],
            ([item[1], item[2], "; ".join(item[3])] for item in profile["usefulExamples"]),
        )
        lines.append("")

    lines += [
        "## E. Existing links",
        "",
        "### Related questions",
        "",
        f"ARIs with at least one related question: **{links['relatedQuestionLinked']:,} "
        f"({fmt_pct(links['relatedQuestionLinked'], n)})**. Median among linked records: "
        f"**{fmt_number(links['relatedQuestionMedianLinked'])}**; maximum: "
        f"**{links['relatedQuestionMaximum']:,}**.",
        "",
    ]
    lines += markdown_table(
        ["Related-question count", "ARIs"],
        links["relatedQuestionDistribution"],
    )
    lines += [
        "",
        "### Existing system-generated related-project links",
        "",
        f"ARIs with at least one embedded UKRI project: **{links['ukriLinked']:,} "
        f"({fmt_pct(links['ukriLinked'], n)})**. Median among linked records: "
        f"**{fmt_number(links['ukriMedianLinked'])}**; maximum: **{links['ukriMaximum']:,}**.",
        f"There are **{links['embeddedProjectObjects']:,}** embedded project-link objects and "
        f"**{links['uniqueProjects']:,}** unique projects using `projectId`, then grant reference/URL "
        f"fallbacks where needed.",
        "",
    ]
    lines += markdown_table(
        ["Related-UKRI-project count", "ARIs"],
        links["ukriDistribution"],
    )
    lines += [
        "",
        f"**Observed ceiling:** {sum(count == links['ukriMaximum'] for count in links['ukriCounts']):,} "
        f"ARIs have exactly the maximum of {links['ukriMaximum']} embedded projects. This strongly "
        "suggests a top-results cap (an inference from the distribution, not an API guarantee), so "
        "the embedded counts should not be treated as exhaustive numbers of relevant projects.",
        "",
        "#### Identifier and URL availability",
        "",
    ]
    lines += markdown_table(
        ["Feature", "Embedded link objects", "Proportion"],
        [
            ["`projectId` present", links["projectIdPresent"], fmt_pct(links["projectIdPresent"], links["embeddedProjectObjects"])],
            ["Grant reference extractable from URL `ref`", links["grantReferenceExtractable"], fmt_pct(links["grantReferenceExtractable"], links["embeddedProjectObjects"])],
            ["Clickable HTTP(S) URL present", links["clickableUrlPresent"], fmt_pct(links["clickableUrlPresent"], links["embeddedProjectObjects"])],
        ],
    )
    lines += [
        "",
        "`projectId` is a project identifier in the live object, but the supplied documentation does "
        "not explicitly guarantee its stability. Grant references are not separate fields; they can "
        "be losslessly parsed from the `ref` query parameter when present.",
        "",
        f"**{links['sharedUniqueProjects']:,} unique UKRI projects** appear against more than one ARI. "
        f"Those shared projects account for **{links['sharedLinkOccurrences']:,}** embedded link "
        f"occurrences. Examples:",
        "",
    ]
    lines += markdown_table(
        ["Project ID", "Grant ref", "ARI count", "Link occurrences", "Project title", "Example ARI IDs"],
        (
            [
                item["projectId"],
                item["grantReference"],
                item["ariCount"],
                item["linkOccurrences"],
                item["title"],
                ", ".join(item["exampleAriIds"]),
            ]
            for item in links["sharedExamples"]
        ),
    )
    link_example_groups = (
        ("Five ARIs with no related UKRI projects", links["noneExamples"]),
        ("Five ARIs with one or two related UKRI projects", links["fewExamples"]),
        ("Five ARIs with many related UKRI projects", links["manyExamples"]),
    )
    for title, example_records in link_example_groups:
        lines += ["", f"#### {title}", ""]
        lines += markdown_table(
            ["ARI ID", "Department", "Projects", "Question"],
            examples_table(example_records, "relatedUKRIProjects"),
        )

    sample_counts = sample_meta["categoryCounts"]
    lines += [
        "",
        "## F. Small meeting sample",
        "",
        f"`ari_sample_{retrieval['filenameDate']}.csv` contains **{len(sample):,}** deliberately "
        f"selected ARIs across **{sample_meta['departmentCount']:,}** departments/agencies. Selection "
        "used deterministic quotas and writes all applicable reasons into `selectionReasons`.",
        "",
    ]
    lines += markdown_table(
        ["Selection property", "Sample records"],
        ([category.replace("_", " "), sample_counts.get(category, 0)] for category in sorted(sample_counts)),
    )
    lines += [
        "",
        f"Short/long are the bottom/top deciles of combined-text length (cutoffs "
        f"{fmt_number(sample_meta['shortCutoff'])} and {fmt_number(sample_meta['longCutoff'])} "
        f"characters). “Many” means at least {sample_meta['manyUkriCutoff']} embedded UKRI projects, "
        "the larger of five and the linked-record upper quartile.",
        "",
        "## G. Questions raised",
        "",
        "## Questions for Kathryn Oliver",
        "",
        "1. Are the existing UKRI links intended to indicate topical relevance, researcher expertise, or both?",
        "2. How were the system-generated UKRI links produced, thresholded, and evaluated, and against what notion of relevance?",
        "3. Should archived ARIs remain searchable in an activity-mapping exercise, and how should supersession be represented?",
        "4. Do departments actively review or use the linked-project feature, and are corrections or relevance judgements retained anywhere?",
        "5. Which combination of question, group, and background should form the semantic representation of an ARI when context is uneven?",
        "6. Should topics, fields of research, and tags be used as retrieval signals, filters, or only explanatory metadata given their duplication and breadth?",
        "7. Which department has enough ARIs, sufficiently usable text, and a credible DEA overlap to serve as a bounded pilot?",
        "8. How should health ARIs be handled when their research and data ecosystem may sit substantially outside the DEA accredited-project register?",
        "9. What language and display safeguards are needed so an unmatched ARI is not misread as an evidence gap or lack of relevant research?",
        "10. Would departments accept activity links as candidate associations requiring review, rather than as claims that research answered an ARI?",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    retrieval = now_metadata()
    date_token = retrieval["filenameDate"]
    raw_path = args.output_dir / f"ari_raw_{date_token}.json"
    csv_path = args.output_dir / f"ari_questions_{date_token}.csv"
    profile_path = args.output_dir / f"ari_profile_{date_token}.md"
    sample_path = args.output_dir / f"ari_sample_{date_token}.csv"
    diagnostic_path = args.output_dir / f"ari_fetch_diagnostic_{date_token}.json"

    try:
        raw = fetch_all_pages(args, retrieval)
    except FetchError as exc:
        diagnostic = {
            "_retrieval": {
                **retrieval,
                "sourceUrl": args.api_url,
                "documentationUrl": DOCUMENTATION_URL,
                "userAgent": USER_AGENT,
                "status": "incomplete",
            },
            "error": str(exc),
            "diagnostic": exc.diagnostic,
        }
        write_json(diagnostic_path, diagnostic)
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"Diagnostic response written to {diagnostic_path}", file=sys.stderr)
        return 1

    # Preserve the complete raw page envelopes before any flattening or profiling.
    write_json(raw_path, raw)
    records = [record for page in raw["pages"] for record in page["data"]]
    fields = ordered_record_fields(records)
    write_flat_csv(csv_path, records, fields)
    sample, sample_meta = select_sample(records)
    write_sample_csv(sample_path, sample, sample_meta)
    report = generate_report(raw, records, sample, sample_meta)
    profile_path.write_text(report, encoding="utf-8")

    archived = sum(bool(record.get("isArchived")) for record in records)
    linked = sum(bool(as_list(record.get("relatedUKRIProjects"))) for record in records)
    print("ARI exploration complete")
    print(f"  retrieved: {raw['_retrieval']['retrievedAtUtc']} UTC")
    print(
        f"  pages: {len(raw['pages'])} exactly once; "
        f"records: {len(records):,}/{raw['_retrieval']['validation']['metadataTotal']:,}"
    )
    print(f"  status: {len(records) - archived:,} current; {archived:,} archived")
    print(f"  embedded UKRI links: {linked:,} ARIs with at least one")
    print(f"  sample: {len(sample)} ARIs across {sample_meta['departmentCount']} departments/agencies")
    for path in (raw_path, csv_path, profile_path, sample_path):
        print(f"  wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
