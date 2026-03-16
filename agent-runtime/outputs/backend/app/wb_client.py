"""
Async WB API client.

Covers:
  - seller-analytics-api: nm-report/detail (list nm_ids) + nm-report/week (stats)
  - advert-api: active campaigns + fullstats

All requests are retried up to 3 times with exponential backoff (1s, 2s, 4s).
"""
import asyncio
import logging
import os
from collections import defaultdict
from datetime import date

import httpx

from app.models import (
    AdvertCampaign,
    AdvertCampaignStat,
    NmDetailResponse,
    NmReportItem,
    NmReportResponse,
)

logger = logging.getLogger(__name__)

_NM_REPORT_BASE = "https://seller-analytics-api.wildberries.ru"
_ADVERT_BASE = "https://advert-api.wildberries.ru"

_RETRY_DELAYS = [1, 2, 4]  # seconds between attempts 1→2, 2→3, 3→fail


class WBClient:
    """Async WB API client.  Instantiate with the WB API token."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._headers = {"Authorization": token}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """Execute an HTTP request with retry + exponential backoff."""
        last_exc: Exception | None = None
        for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
            if delay:
                logger.warning(
                    "Retrying %s %s (attempt %d) after %ds backoff",
                    method,
                    url,
                    attempt,
                    delay,
                )
                await asyncio.sleep(delay)
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.request(
                        method, url, headers=self._headers, **kwargs
                    )
                    response.raise_for_status()
                    return response
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                if isinstance(exc, httpx.HTTPStatusError):
                    logger.error(
                        "WB API error on attempt %d: %s %s → HTTP %d",
                        attempt, method, url, exc.response.status_code,
                    )
                else:
                    logger.error(
                        "WB API error on attempt %d: %s %s → %s",
                        attempt, method, url, type(exc).__name__,
                    )
                last_exc = exc
        raise RuntimeError(
            f"WB API request failed after {len(_RETRY_DELAYS) + 1} attempts: "
            f"{method} {url}"
        ) from last_exc

    # ------------------------------------------------------------------
    # nm-report API
    # ------------------------------------------------------------------

    async def get_nm_ids(self) -> list[int]:
        """Fetch all nm_ids for the account using cursor-based pagination.

        Calls GET /api/v2/nm-report/detail with limit=1000, incrementing offset
        until isNextPage is False or the response contains no cards.
        """
        nm_ids: list[int] = []
        limit = 1000
        offset = 0

        while True:
            url = (
                f"{_NM_REPORT_BASE}/api/v2/nm-report/detail"
                f"?limit={limit}&offset={offset}"
            )
            response = await self._request("GET", url)
            parsed = NmDetailResponse.model_validate(response.json())

            if parsed.error:
                logger.error(
                    "WB nm-report/detail returned error: %s", parsed.errorText
                )
                break

            cards = parsed.data.cards
            if not cards:
                break

            nm_ids.extend(card.nmID for card in cards)

            if not parsed.data.isNextPage:
                break

            offset += limit

        logger.info("Fetched %d nm_ids", len(nm_ids))
        return nm_ids

    async def get_nm_report(
        self,
        nm_ids: list[int],
        start_date: date,
        end_date: date,
    ) -> list[NmReportItem]:
        """Fetch weekly nm-report stats and aggregate per-nm totals.

        Calls POST /api/v2/nm-report/week.
        Passing an empty nmIDs list returns stats for all nm_ids on the account.
        """
        url = f"{_NM_REPORT_BASE}/api/v2/nm-report/week"
        payload = {
            "nmIDs": nm_ids,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "aggregationLevel": "day",
        }
        response = await self._request("POST", url, json=payload)
        parsed = NmReportResponse.model_validate(response.json())

        if parsed.error:
            logger.error("WB nm-report/week returned error: %s", parsed.errorText)
            return []

        # Aggregate daily stats → weekly totals
        for item in parsed.data:
            item.total_views = sum(d.views for d in item.statistics)
            item.total_clicks = sum(d.clicks for d in item.statistics)
            item.total_cart = sum(d.addToCartCount for d in item.statistics)
            item.total_buyouts = sum(d.buyoutsCount for d in item.statistics)
            item.total_sum_rub = sum(d.buyoutsSumRub for d in item.statistics)

        logger.info("Fetched nm-report stats for %d items", len(parsed.data))
        return parsed.data

    # ------------------------------------------------------------------
    # Advert API
    # ------------------------------------------------------------------

    async def get_active_campaigns(self) -> list[int]:
        """Return list of campaign IDs with status=9 (active/running)."""
        url = f"{_ADVERT_BASE}/adv/v1/promotion/adverts?status=9"
        response = await self._request("GET", url)

        raw = response.json()
        if not raw:
            logger.info("No active advert campaigns found")
            return []

        campaigns = [AdvertCampaign.model_validate(item) for item in raw]
        ids = [c.advertId for c in campaigns]
        logger.info("Found %d active advert campaigns", len(ids))
        return ids

    async def get_advert_fullstats(
        self,
        campaign_ids: list[int],
        dates: list[str],
    ) -> list[AdvertCampaignStat]:
        """Fetch fullstats for given campaign IDs over the supplied dates.

        Batches requests to 100 campaigns per call (API limit).
        """
        if not campaign_ids:
            return []

        url = f"{_ADVERT_BASE}/adv/v3/fullstats"
        batch_size = 100
        all_stats: list[AdvertCampaignStat] = []

        for i in range(0, len(campaign_ids), batch_size):
            batch = campaign_ids[i : i + batch_size]
            payload = [{"id": cid, "dates": dates} for cid in batch]
            response = await self._request("POST", url, json=payload)

            raw = response.json()
            if not raw:
                continue

            stats = [AdvertCampaignStat.model_validate(item) for item in raw]
            all_stats.extend(stats)

        logger.info(
            "Fetched advert fullstats for %d campaigns (%d batches)",
            len(campaign_ids),
            (len(campaign_ids) + batch_size - 1) // batch_size,
        )
        return all_stats

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_advert_by_nm(
        self,
        fullstats: list[AdvertCampaignStat],
    ) -> dict[int, float]:
        """Aggregate total ad spend per nm_id across all campaigns and days.

        If an nm_id does not appear in fullstats its key is absent from the
        returned dict; callers should use `.get(nm_id, 0.0)`.
        """
        result: dict[int, float] = defaultdict(float)
        for campaign in fullstats:
            for day in campaign.days:
                for app in day.apps:
                    for nm in app.nm:
                        result[nm.nmId] += nm.sum
        return dict(result)
