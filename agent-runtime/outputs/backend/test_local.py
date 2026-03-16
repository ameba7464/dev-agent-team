"""Run the pipeline directly (no HTTP server needed)."""
import asyncio
import os
from pathlib import Path

# Load .env
env_file = Path(__file__).parent / ".env"
for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.date_utils import get_previous_week_range
from app.sheets_writer import create_weekly_sheet
from app.wb_client import WBClient
from datetime import timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def main():
    token = os.environ["WB_STATS_TOKEN"]
    client = WBClient(token)

    start_date, end_date = get_previous_week_range()
    print(f"Week: {start_date} — {end_date}")

    print("Fetching nm_ids...")
    nm_ids = await client.get_nm_ids()
    print(f"Found {len(nm_ids)} nm_ids")

    print("Fetching nm-report stats...")
    nm_items = await client.get_nm_report(nm_ids, start_date, end_date)
    print(f"Got stats for {len(nm_items)} items")

    print("Fetching advert campaigns...")
    campaign_ids = await client.get_active_campaigns()
    print(f"Found {len(campaign_ids)} active campaigns")

    dates = [(start_date + timedelta(days=i)).isoformat() for i in range(7)]
    print("Fetching advert fullstats...")
    fullstats = await client.get_advert_fullstats(campaign_ids, dates)
    advert_by_nm = client.aggregate_advert_by_nm(fullstats)
    print(f"Advert data for {len(advert_by_nm)} nm_ids")

    print("Creating Google Spreadsheet...")
    sheet_url = create_weekly_sheet(nm_items, advert_by_nm, start_date, end_date)
    print(f"\n✓ Done! Sheet URL: {sheet_url}")

asyncio.run(main())
