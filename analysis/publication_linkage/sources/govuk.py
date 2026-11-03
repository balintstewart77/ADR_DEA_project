"""GOV.UK search and content APIs: government analysts' reports.

* Search: ``GET https://www.gov.uk/api/search.json?q=...&count=...&start=...
  &fields=...&filter_content_purpose_supergroup=research_and_statistics``
  (repeat ``fields`` per field). If the supergroup filter is rejected the
  query is retried without it.
* Content: ``GET https://www.gov.uk/api/content<link>`` for the page body
  (attachments on assets.publishing.service.gov.uk are not fetched).

Queries pair each register dataset in scope with "Secure Research Service",
"Integrated Data Service" or "Digital Economy Act". GOV.UK pages rarely carry
author metadata, so author evidence comes from register researcher names
appearing in the page body.
"""

from __future__ import annotations

from datetime import date

from analysis.publication_linkage import config
from analysis.publication_linkage.http_client import CachedClient, QueryRejected
from analysis.publication_linkage.matching import clean_text, dataset_name_variants
from analysis.publication_linkage.outputs import CandidateOutput
from analysis.publication_linkage.register_records import ProjectRecord

SEARCH = "https://www.gov.uk/api/search.json"
CONTENT = "https://www.gov.uk/api/content"
ROUTE_TERMS = ('"Secure Research Service"', '"Integrated Data Service"', '"Digital Economy Act"')
FIELDS = ["title", "link", "description", "public_timestamp", "organisations", "content_store_document_type"]
COUNT = 50


class GovUkSource:
    name = "govuk"

    def __init__(self, *, offline: bool = False, cache_dir=config.CACHE_DIR):
        self.client = CachedClient("govuk", offline=offline, cache_dir=cache_dir)
        self.notes: list[str] = []
        self._supergroup_ok = True

    def search(self, query: str) -> list[dict]:
        params = {"q": query, "count": COUNT, "fields": FIELDS}
        if self._supergroup_ok:
            params["filter_content_purpose_supergroup"] = "research_and_statistics"
        try:
            data, _ = self.client.get_json(SEARCH, params=params)
        except QueryRejected:
            if not self._supergroup_ok:
                raise
            self._supergroup_ok = False
            self.notes.append("supergroup filter rejected; searching all content")
            return self.search(query)
        return (data or {}).get("results") or []

    def content(self, link: str) -> dict:
        data, _ = self.client.get_json(f"{CONTENT}{link}")
        return data or {}

    @staticmethod
    def body_text(content: dict) -> str:
        details = content.get("details") or {}
        parts = [details.get("body"), content.get("description")]
        for key in ("documents", "headers"):
            value = details.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
        return clean_text(" ".join(str(part) for part in parts if part))

    def collect(self, projects: list[ProjectRecord], snapshot_date: date) -> list[CandidateOutput]:
        labels: list[str] = []
        for project in projects:
            for dataset in project.datasets:
                variants = [label for label, kind in dataset_name_variants(dataset) if kind == "name"]
                if variants:
                    labels.append(min(variants, key=len))
        candidates: dict[str, CandidateOutput] = {}
        for label in dict.fromkeys(labels):
            for route in ROUTE_TERMS:
                for result in self.search(f'"{label}" {route}'):
                    link = result.get("link") or ""
                    if not link.startswith("/") or link in candidates:
                        continue
                    page = self.content(link)
                    organisations = [o.get("title", "") for o in result.get("organisations") or [] if isinstance(o, dict)]
                    candidates[link] = CandidateOutput(
                        source="govuk",
                        source_id=link,
                        title=result.get("title") or page.get("title") or "",
                        publication_date=(result.get("public_timestamp") or page.get("first_published_at") or "")[:10] or None,
                        authors=[],
                        venue="; ".join(organisations) or "GOV.UK",
                        type_raw=result.get("content_store_document_type") or page.get("document_type"),
                        abstract=result.get("description"),
                        full_text=self.body_text(page),
                        url=f"https://www.gov.uk{link}",
                        query=f"govuk:{label}|{route}",
                    )
        return list(candidates.values())
