"""
Elexon BMRS API client for FUELHH actuals and WINDFOR forecasts.
Handles streaming endpoints, timeouts, errors, normalization, and in-memory caching.
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import httpx
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
DEFAULT_TIMEOUT_SECONDS = 30.0


class ElexonAPIError(Exception):
    """Raised when Elexon BMRS returns an error or is unreachable."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class ElexonClient:
    """Async client for fetching and caching Elexon BMRS datasets."""

    def __init__(self, base_url: str = ELEXON_BASE_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = base_url
        self.timeout = timeout
        self._fuelhh_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._windfor_cache: Dict[str, List[Dict[str, Any]]] = {}

    @staticmethod
    def normalize_utc(timestamp_str: str) -> str:
        """
        Normalize any ISO timestamp string into a canonical UTC ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ.
        Raises ValueError if unparseable.
        """
        if not timestamp_str:
            raise ValueError("Empty timestamp string")
        dt = date_parser.isoparse(timestamp_str)
        # Convert to UTC if tz-aware, else assume UTC as per Elexon schema
        if dt.tzinfo is not None:
            from datetime import timezone
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def fetch_fuelhh_actuals(
        self,
        date_from: date,
        date_to: date
    ) -> List[Dict[str, Any]]:
        """
        Fetch FUELHH actuals stream for the settlement date range, filtered to fuelType == 'WIND'.
        Results are cached by date range.
        """
        cache_key = f"fuelhh_{date_from.isoformat()}_{date_to.isoformat()}"
        if cache_key in self._fuelhh_cache:
            logger.info("Serving FUELHH actuals from cache for %s to %s", date_from, date_to)
            return self._fuelhh_cache[cache_key]

        url = f"{self.base_url}/datasets/FUELHH/stream"
        params = {
            "settlementDateFrom": date_from.isoformat(),
            "settlementDateTo": date_to.isoformat()
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
        except httpx.RequestError as exc:
            logger.error("Network error communicating with Elexon FUELHH: %s", exc)
            raise ElexonAPIError(f"Failed to connect to Elexon BMRS FUELHH: {str(exc)}", status_code=502)

        if response.status_code != 200:
            logger.error("Elexon FUELHH returned HTTP %s: %s", response.status_code, response.text[:300])
            raise ElexonAPIError(
                f"Elexon BMRS FUELHH error HTTP {response.status_code}: {response.text[:200]}",
                status_code=502
            )

        try:
            raw_data = response.json()
        except Exception as exc:
            raise ElexonAPIError(f"Failed to parse Elexon FUELHH JSON: {str(exc)}", status_code=502)

        if not isinstance(raw_data, list):
            # In case wrapper is returned: {"data": [...]}
            if isinstance(raw_data, dict) and "data" in raw_data and isinstance(raw_data["data"], list):
                raw_data = raw_data["data"]
            else:
                raise ElexonAPIError("Elexon FUELHH returned unexpected non-array format", status_code=502)

        # Filter to WIND and clean records
        validated_records: List[Dict[str, Any]] = []
        for record in raw_data:
            if not isinstance(record, dict):
                continue
            if record.get("fuelType") != "WIND":
                continue

            raw_start = record.get("startTime")
            raw_gen = record.get("generation")
            if raw_start is None or raw_gen is None:
                continue

            try:
                norm_start = self.normalize_utc(str(raw_start))
                gen_mw = float(raw_gen)
            except (ValueError, TypeError):
                continue

            validated_records.append({
                "dataset": "FUELHH",
                "fuelType": "WIND",
                "startTime": norm_start,
                "settlementDate": record.get("settlementDate"),
                "settlementPeriod": record.get("settlementPeriod"),
                "publishTime": self.normalize_utc(str(record.get("publishTime"))) if record.get("publishTime") else None,
                "generation": gen_mw
            })

        self._fuelhh_cache[cache_key] = validated_records
        logger.info("Fetched and cached %d WIND actuals from FUELHH", len(validated_records))
        return validated_records

    async def fetch_windfor_vintages(
        self,
        publish_from: datetime,
        publish_to: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetch WINDFOR forecast stream published between publish_from and publish_to.
        Preserves all publication vintages.
        """
        cache_key = f"windfor_{publish_from.strftime('%Y%m%dT%H%M%SZ')}_{publish_to.strftime('%Y%m%dT%H%M%SZ')}"
        if cache_key in self._windfor_cache:
            logger.info("Serving WINDFOR from cache for key %s", cache_key)
            return self._windfor_cache[cache_key]

        url = f"{self.base_url}/datasets/WINDFOR/stream"
        params = {
            "publishDateTimeFrom": publish_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": publish_to.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
        except httpx.RequestError as exc:
            logger.error("Network error communicating with Elexon WINDFOR: %s", exc)
            raise ElexonAPIError(f"Failed to connect to Elexon BMRS WINDFOR: {str(exc)}", status_code=502)

        if response.status_code != 200:
            logger.error("Elexon WINDFOR returned HTTP %s: %s", response.status_code, response.text[:300])
            raise ElexonAPIError(
                f"Elexon BMRS WINDFOR error HTTP {response.status_code}: {response.text[:200]}",
                status_code=502
            )

        try:
            raw_data = response.json()
        except Exception as exc:
            raise ElexonAPIError(f"Failed to parse Elexon WINDFOR JSON: {str(exc)}", status_code=502)

        if not isinstance(raw_data, list):
            if isinstance(raw_data, dict) and "data" in raw_data and isinstance(raw_data["data"], list):
                raw_data = raw_data["data"]
            else:
                raise ElexonAPIError("Elexon WINDFOR returned unexpected non-array format", status_code=502)

        validated_records: List[Dict[str, Any]] = []
        for record in raw_data:
            if not isinstance(record, dict):
                continue
            raw_start = record.get("startTime")
            raw_pub = record.get("publishTime")
            raw_gen = record.get("generation")
            if raw_start is None or raw_pub is None or raw_gen is None:
                continue

            try:
                norm_start = self.normalize_utc(str(raw_start))
                norm_pub = self.normalize_utc(str(raw_pub))
                gen_mw = float(raw_gen)
            except (ValueError, TypeError):
                continue

            validated_records.append({
                "dataset": "WINDFOR",
                "publishTime": norm_pub,
                "startTime": norm_start,
                "generation": gen_mw
            })

        self._windfor_cache[cache_key] = validated_records
        logger.info("Fetched and cached %d WINDFOR records", len(validated_records))
        return validated_records

    def clear_cache(self):
        """Clears in-memory caches."""
        self._fuelhh_cache.clear()
        self._windfor_cache.clear()

    @property
    def cache_stats(self) -> Dict[str, int]:
        return {
            "fuelhh_keys": len(self._fuelhh_cache),
            "windfor_keys": len(self._windfor_cache),
            "fuelhh_total_records": sum(len(v) for v in self._fuelhh_cache.values()),
            "windfor_total_records": sum(len(v) for v in self._windfor_cache.values()),
        }
