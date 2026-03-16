"""
Vercel Serverless entry point.

Route:  GET /api/weekly_report
Trigger: Vercel Cron — every Wednesday at 17:00 UTC (20:00 MSK)

The handler:
1. Validates the Authorization header against CRON_SECRET.
2. Determines the previous full calendar week (Mon–Sun).
3. Calls WBClient to collect nm-report + advert stats.
4. Writes a new Google Spreadsheet via sheets_writer.
5. Returns JSON with the sheet URL and week label.
"""
import asyncio
import json
import logging
import os
import sys
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that `app.*` imports work both
# locally and inside the Vercel runtime.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.date_utils import get_previous_week_range
from app.sheets_writer import create_weekly_sheet
from app.wb_client import WBClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Async pipeline
# ---------------------------------------------------------------------------


async def _run_pipeline(start_date: date, end_date: date) -> str:
    """Execute the full WB → Google Sheets pipeline and return the sheet URL."""
    token = os.environ["WB_STATS_TOKEN"]
    client = WBClient(token)

    logger.info("Fetching nm_ids for the account...")
    nm_ids = await client.get_nm_ids()

    logger.info("Fetching nm-report stats %s — %s", start_date, end_date)
    nm_items = await client.get_nm_report(nm_ids, start_date, end_date)

    logger.info("Fetching active advert campaigns...")
    campaign_ids = await client.get_active_campaigns()

    # Build list of date strings for the week
    dates = [
        (start_date + timedelta(days=i)).isoformat()
        for i in range((end_date - start_date).days + 1)
    ]

    logger.info("Fetching advert fullstats for %d campaigns...", len(campaign_ids))
    fullstats = await client.get_advert_fullstats(campaign_ids, dates)

    advert_by_nm = client.aggregate_advert_by_nm(fullstats)

    logger.info("Creating Google Spreadsheet...")
    sheet_url = create_weekly_sheet(nm_items, advert_by_nm, start_date, end_date)
    return sheet_url


# ---------------------------------------------------------------------------
# Vercel handler
# ---------------------------------------------------------------------------


class handler(BaseHTTPRequestHandler):
    """Vercel Python Serverless Function handler (sync BaseHTTPRequestHandler)."""

    def do_GET(self) -> None:  # noqa: N802
        # --- Authorization check ---
        cron_secret = os.environ.get("CRON_SECRET", "")
        auth_header = self.headers.get("Authorization", "")
        expected = f"Bearer {cron_secret}"

        if not cron_secret or auth_header != expected:
            self._send_json(401, {"status": "error", "message": "Unauthorized"})
            return

        # --- Pipeline ---
        try:
            start_date, end_date = get_previous_week_range()
            week_label = f"{start_date} — {end_date}"
            logger.info("Starting pipeline for week: %s", week_label)

            sheet_url = asyncio.run(_run_pipeline(start_date, end_date))

            self._send_json(
                200,
                {
                    "status": "ok",
                    "sheet_url": sheet_url,
                    "week": week_label,
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Pipeline failed: %s", exc, exc_info=True)
            self._send_json(
                500,
                {
                    "status": "error",
                    "message": "Pipeline execution failed. Check server logs for details.",
                },
            )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # noqa: D102
        logger.info(fmt, *args)
