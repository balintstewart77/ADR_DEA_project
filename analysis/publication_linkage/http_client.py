"""Cached, polite HTTP access for the publication-linkage sources.

* Every successful (2xx) or definitive (404) raw response is cached on disk
  under ``data/publication_linkage_cache/<source>/``; runs are resumable and a
  re-run with a warm cache makes no network calls.
* Secrets (API keys) never enter cache keys, cached request records, logs or
  exceptions: secret query parameters are dropped before hashing/logging and
  any configured secret value is redacted from text.
* Live calls are spaced per source, retried on 429/5xx/network errors with
  exponential backoff (2, 4, 8, 16 s) and ``Retry-After`` honoured.
* A proxy/policy refusal (HTTP 403 on CONNECT, DNS failure) marks the source
  as blocked for the rest of the run instead of hammering it.
* OpenAlex spend is tracked per UTC day from each response's reported cost;
  calls stop before the configured ceiling.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from analysis.publication_linkage import config


class SourceBlocked(RuntimeError):
    """The network policy (or DNS) refused the host."""


class BudgetExhausted(RuntimeError):
    """The daily OpenAlex budget ceiling would be exceeded."""


class QueryRejected(RuntimeError):
    """The API rejected the query itself (not a transient failure)."""


@dataclass
class SourceStats:
    live_calls: int = 0
    cached_calls: int = 0
    errors: int = 0
    retries: int = 0
    blocked: bool = False
    blocked_reason: str = ""
    cost_usd: float = 0.0
    seconds: float = 0.0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "live_calls": self.live_calls,
            "cached_calls": self.cached_calls,
            "errors": self.errors,
            "retries": self.retries,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "cost_usd": round(self.cost_usd, 6),
            "seconds_live": round(self.seconds, 1),
            "notes": sorted(set(self.notes)),
        }


class OpenAlexBudget:
    """Per-UTC-day spend ledger stored next to the cache.

    Two stops, whichever bites first: our own ledger of each response's
    ``meta.cost_usd``, and OpenAlex's server-side daily credit counter
    (``X-RateLimit-Remaining`` of ``X-RateLimit-Limit``; 10,000 credits = $1
    on a free key, verified live 2026-11-03), which also counts any other use
    of the key that day.
    """

    USD_PER_CREDIT = 0.0001

    def __init__(self, cache_dir: Path, stop_at_usd: float = config.OPENALEX_STOP_AT_USD):
        self.path = cache_dir / "openalex" / "usage_ledger.json"
        self.stop_at_usd = stop_at_usd
        self._lock = threading.Lock()

    def server_spent_today(self) -> float | None:
        """Spend implied by the last server credit counter seen today."""
        day = self._load().get(self.today(), {})
        limit, remaining = day.get("server_limit_credits"), day.get("server_remaining_credits")
        if limit is None or remaining is None:
            return None
        return (float(limit) - float(remaining)) * self.USD_PER_CREDIT

    @staticmethod
    def today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def spent_today(self) -> float:
        return float(self._load().get(self.today(), {}).get("cost_usd", 0.0))

    def check(self, expected_cost: float) -> None:
        spent = max(self.spent_today(), self.server_spent_today() or 0.0)
        if spent + expected_cost > self.stop_at_usd:
            raise BudgetExhausted(
                f"OpenAlex spend today {spent:.4f} USD + {expected_cost:.4f} would pass "
                f"the {self.stop_at_usd:.2f} USD stop; resume after midnight UTC"
            )

    def record(self, cost: float, kind: str, headers=None) -> None:
        with self._lock:
            ledger = self._load()
            day = ledger.setdefault(self.today(), {"cost_usd": 0.0, "calls": {}})
            day["cost_usd"] = round(float(day["cost_usd"]) + cost, 6)
            day["calls"][kind] = int(day["calls"].get(kind, 0)) + 1
            if headers is not None:
                try:
                    if headers.get("X-RateLimit-Limit") is not None:
                        day["server_limit_credits"] = int(float(headers["X-RateLimit-Limit"]))
                    if headers.get("X-RateLimit-Remaining") is not None:
                        day["server_remaining_credits"] = int(float(headers["X-RateLimit-Remaining"]))
                except (TypeError, ValueError):
                    pass
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _retry_after_seconds(response: requests.Response, attempt: int) -> float:
    default = 2.0 ** (attempt + 1)
    header = response.headers.get("Retry-After") or response.headers.get("X-RateLimit-Retry-After")
    if not header:
        return default
    try:
        return max(1.0, min(120.0, float(header)))
    except ValueError:
        pass
    for parser in (parsedate_to_datetime, lambda v: datetime.strptime(v, "%Y-%m-%dT%H:%M:%S%z")):
        try:
            when = parser(header)
            return max(1.0, min(120.0, (when - datetime.now(timezone.utc)).total_seconds()))
        except (TypeError, ValueError):
            continue
    return default


def _is_policy_block(error: Exception) -> bool:
    text = str(error)
    return (
        isinstance(error, requests.exceptions.ProxyError)
        and ("403" in text or "407" in text or "Tunnel connection failed" in text)
    ) or "Name or service not known" in text or "getaddrinfo" in text or "NameResolutionError" in text


class CachedClient:
    """HTTP client for one source."""

    KEEP_HEADERS = (
        "content-type", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-retry-after",
        "x-ratelimit-credits-used", "x-ratelimit-reset", "retry-after",
    )

    def __init__(
        self,
        source: str,
        *,
        cache_dir: Path = config.CACHE_DIR,
        headers: dict[str, str] | None = None,
        secret_params: tuple[str, ...] = (),
        min_interval: float | None = None,
        offline: bool = False,
        session: requests.Session | None = None,
        max_retries: int = config.MAX_RETRIES,
        backoff_base: float = 2.0,
    ):
        self.source = source
        self.cache_root = Path(cache_dir)
        self.cache_dir = self.cache_root / source
        self.headers = {"User-Agent": config.USER_AGENT, **(headers or {})}
        self.secret_params = secret_params
        self.min_interval = config.MIN_INTERVAL_SECONDS.get(source, 0.5) if min_interval is None else min_interval
        self.offline = offline
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.stats = SourceStats()
        self._last_call = 0.0
        self._lock = threading.Lock()
        self.call_log = self.cache_root / "call_log.jsonl"

    # -- cache -----------------------------------------------------------
    def _public_params(self, params: dict | None) -> dict:
        return {k: v for k, v in sorted((params or {}).items()) if k not in self.secret_params}

    def cache_key(self, method: str, url: str, params: dict | None, body: Any = None, variant: str = "") -> str:
        material = json.dumps(
            {"m": method.upper(), "u": url, "p": self._public_params(params), "b": body, "v": variant},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / key[:2] / f"{key}.json"

    def _read_cache(self, key: str) -> dict | None:
        path = self._cache_path(key)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _write_cache(self, key: str, record: dict) -> None:
        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(config.redact(json.dumps(record, ensure_ascii=False)), encoding="utf-8")
        tmp.replace(path)

    def _log(self, entry: dict) -> None:
        self.call_log.parent.mkdir(parents=True, exist_ok=True)
        with self.call_log.open("a", encoding="utf-8") as handle:
            handle.write(config.redact(json.dumps(entry, ensure_ascii=False, default=str)) + "\n")

    # -- requests ----------------------------------------------------------
    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json_body: Any = None,
        headers: dict | None = None,
        expected_cost: float = 0.0,
        budget: OpenAlexBudget | None = None,
        cost_kind: str = "",
        accept_statuses: tuple[int, ...] = (200, 404),
        cache_variant: str = "",
    ) -> dict:
        """Return the cached record ``{"status", "body", "headers", ...}``."""
        key = self.cache_key(method, url, params, json_body, cache_variant + json.dumps(headers or {}, sort_keys=True))
        cached = self._read_cache(key)
        if cached is not None:
            self.stats.cached_calls += 1
            if cached.get("rejected"):
                # A definitive query rejection is replayed, so offline runs
                # take the same fallback paths as the live run did.
                raise QueryRejected(f"{self.source} {cached.get('status')}: {cached.get('body', '')[:300]}")
            return cached
        if self.offline:
            raise SourceBlocked(f"{self.source}: offline mode and no cached response")
        if self.stats.blocked:
            raise SourceBlocked(f"{self.source}: blocked earlier in this run ({self.stats.blocked_reason})")
        if budget is not None:
            budget.check(expected_cost)

        public_url = url + ("?" + urlencode(self._public_params(params)) if params else "")
        attempt = 0
        while True:
            with self._lock:
                wait = self.min_interval - (time.monotonic() - self._last_call)
                if wait > 0:
                    time.sleep(wait)
                self._last_call = time.monotonic()
            started = time.monotonic()
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers={**self.headers, **(headers or {})},
                    timeout=config.REQUEST_TIMEOUT_SECONDS,
                )
            except requests.exceptions.RequestException as error:
                elapsed = time.monotonic() - started
                self.stats.seconds += elapsed
                if _is_policy_block(error):
                    self.stats.blocked = True
                    self.stats.blocked_reason = "network policy refused host (proxy 403 / DNS)"
                    self._log({"ts": _now(), "source": self.source, "url": public_url, "outcome": "blocked"})
                    raise SourceBlocked(f"{self.source}: {self.stats.blocked_reason}") from None
                if attempt < self.max_retries:
                    self.stats.retries += 1
                    time.sleep(self.backoff_base ** (attempt + 1))
                    attempt += 1
                    continue
                self.stats.errors += 1
                self._log({"ts": _now(), "source": self.source, "url": public_url, "outcome": f"error: {type(error).__name__}"})
                raise
            elapsed = time.monotonic() - started
            self.stats.seconds += elapsed
            self.stats.live_calls += 1
            kept_headers = {k: v for k, v in response.headers.items() if k.lower() in self.KEEP_HEADERS}
            cost = 0.0
            if budget is not None:
                cost = _reported_openalex_cost(response, expected_cost)
                budget.record(cost, cost_kind or "call", response.headers)
                self.stats.cost_usd += cost
            self._log({
                "ts": _now(), "source": self.source, "method": method, "url": public_url,
                "status": response.status_code, "seconds": round(elapsed, 2), "cost_usd": cost,
                "ratelimit_remaining": kept_headers.get("X-Ratelimit-Remaining") or kept_headers.get("X-RateLimit-Remaining"),
            })
            if response.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                if response.status_code == 500 and _looks_like_query_error(response):
                    break
                self.stats.retries += 1
                time.sleep(max(_retry_after_seconds(response, attempt), self.backoff_base ** (attempt + 1)))
                attempt += 1
                continue
            break

        self._pace_on_ratelimit(response)
        if response.status_code not in accept_statuses:
            self.stats.errors += 1
            message = config.redact(response.text[:300])
            if _looks_like_query_error(response) or response.status_code in (400, 422):
                self._write_cache(key, {
                    "request": {"method": method, "url": url, "params": self._public_params(params), "json": json_body},
                    "status": response.status_code,
                    "rejected": True,
                    "fetched_at": _now(),
                    "body": response.text[:2000],
                })
                raise QueryRejected(f"{self.source} {response.status_code}: {message}")
            raise RuntimeError(f"{self.source} HTTP {response.status_code}: {message}")
        record = {
            "request": {"method": method, "url": url, "params": self._public_params(params), "json": json_body},
            "status": response.status_code,
            "headers": kept_headers,
            "fetched_at": _now(),
            "body": response.text,
        }
        self._write_cache(key, record)
        return record

    def get_json(self, url: str, **kwargs) -> tuple[Any, dict]:
        record = self.request("GET", url, **kwargs)
        return _parse_json(record), record

    def post_json(self, url: str, body: Any, **kwargs) -> tuple[Any, dict]:
        record = self.request("POST", url, json_body=body, **kwargs)
        return _parse_json(record), record

    def get_text(self, url: str, **kwargs) -> tuple[str, dict]:
        record = self.request("GET", url, **kwargs)
        return record.get("body") or "", record

    def _pace_on_ratelimit(self, response: requests.Response) -> None:
        remaining = response.headers.get("X-RateLimit-Remaining") or response.headers.get("X-Ratelimit-Remaining")
        try:
            if remaining is not None and int(float(remaining)) <= 1:
                time.sleep(_retry_after_seconds(response, 0))
        except ValueError:
            pass


def _parse_json(record: dict) -> Any:
    if record.get("status") == 404:
        return None
    body = record.get("body") or ""
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _looks_like_query_error(response: requests.Response) -> bool:
    text = response.text[:500]
    return "not a searchable field" in text or "Invalid expression" in text or "Illegal arguments" in text


def _reported_openalex_cost(response: requests.Response, fallback: float) -> float:
    """Cost from ``meta.cost`` (USD) or the credits header; else the list price."""
    try:
        meta = response.json().get("meta") or {}
        for key in ("cost_usd", "cost"):
            if key in meta and meta[key] is not None:
                return float(meta[key])
    except (ValueError, AttributeError):
        pass
    header = response.headers.get("X-RateLimit-Credits-Used")
    if header:
        try:
            value = float(header)
            # Older credit-based responses report integer credits, not USD.
            return value if value < 1 else fallback
        except ValueError:
            pass
    return fallback


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
