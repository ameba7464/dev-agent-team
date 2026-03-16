"""
Google Sheets writer.

Creates a new spreadsheet per weekly run, populates it with nm-report data,
and formats the sheet.  All computed metrics are written as Google Sheets
formulas (not pre-calculated numbers) so the spreadsheet remains auditable.
"""
import base64
import json
import logging
import os
from datetime import date

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build  # type: ignore

from app.models import NmReportItem

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_HEADERS = [
    "Неделя",
    "Товарная позиция",
    "Показы",
    "Переходы",
    "Корзины",
    "Выкупы",
    "Сумма продаж",
    "Внутр. реклама",
    "CTR",
    "CR в корзину",
    "CR в выкуп",
    "Средний чек",
    "ДРР",
]


def _get_credentials() -> Credentials:
    """Decode GOOGLE_CREDENTIALS (base64 JSON) and return a Credentials object."""
    raw_b64 = os.environ["GOOGLE_CREDENTIALS"]
    try:
        raw_json = base64.b64decode(raw_b64)
    except Exception:
        raise ValueError("Failed to decode GOOGLE_CREDENTIALS. Ensure it is valid base64.")
    try:
        creds_dict = json.loads(raw_json)
    except Exception:
        raise ValueError("Failed to parse GOOGLE_CREDENTIALS. Ensure it contains valid JSON.")
    return Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)


def _get_gspread_client() -> gspread.Client:
    """Return an authorised gspread client."""
    creds = _get_credentials()
    return gspread.authorize(creds)


def _formula_row(row: int) -> list:
    """Return the formula cells (columns I–M) for a given 1-indexed sheet row."""
    return [
        f"=IF(C{row}=0,0,D{row}/C{row})",      # I  CTR
        f"=IF(D{row}=0,0,E{row}/D{row})",       # J  CR в корзину
        f"=IF(D{row}=0,0,F{row}/D{row})",       # K  CR в выкуп
        f"=IF(F{row}=0,0,G{row}/F{row})",       # L  Средний чек
        f"=IF(G{row}=0,0,H{row}/G{row})",       # M  ДРР
    ]


def create_weekly_sheet(
    nm_items: list[NmReportItem],
    advert_by_nm: dict[int, float],
    date_from: date,
    date_to: date,
) -> str:
    """Create a new Google Spreadsheet with the weekly WB stats.

    Args:
        nm_items:     Aggregated nm-report items from WBClient.
        advert_by_nm: Dict mapping nm_id → total ad spend for the week.
        date_from:    Start date of the reporting period (Monday).
        date_to:      End date of the reporting period (Sunday).

    Returns:
        URL of the created spreadsheet.
    """
    folder_id = os.environ["GOOGLE_FOLDER_ID"]
    creds = _get_credentials()
    gc = gspread.authorize(creds)

    sheet_name = f"WB Stats {date_from} — {date_to}"
    logger.info("Creating spreadsheet: %s", sheet_name)
    spreadsheet = gc.create(sheet_name)

    # Move to the designated Drive folder
    drive_service = build("drive", "v3", credentials=creds)
    drive_service.files().update(
        fileId=spreadsheet.id,
        addParents=folder_id,
        removeParents="root",
        fields="id, parents",
    ).execute()
    logger.info("Spreadsheet moved to folder %s", folder_id)

    ws = spreadsheet.sheet1

    # --- Header row ---
    ws.append_row(_HEADERS, value_input_option="USER_ENTERED")

    # --- Data rows ---
    week_label = f"{date_from} — {date_to}"
    rows: list[list] = []

    for idx, item in enumerate(nm_items):
        row_num = idx + 2  # sheet rows are 1-indexed; row 1 = header
        spend = advert_by_nm.get(item.nmID, 0.0)

        week_cell = week_label if idx == 0 else ""

        data_cells = [
            week_cell,                   # A  Неделя
            item.imtName,                # B  Товарная позиция
            item.total_views,            # C  Показы
            item.total_clicks,           # D  Переходы
            item.total_cart,             # E  Корзины
            item.total_buyouts,          # F  Выкупы
            item.total_sum_rub,          # G  Сумма продаж
            spend,                       # H  Внутр. реклама
        ]
        data_cells.extend(_formula_row(row_num))
        rows.append(data_cells)

    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")

    # --- ИТОГО row ---
    last_data_row = 1 + len(nm_items)  # last row with product data
    total_row = last_data_row + 1

    total_row_data = [
        "",                                          # A
        "ИТОГО",                                     # B
        f"=SUM(C2:C{last_data_row})",               # C  Показы
        f"=SUM(D2:D{last_data_row})",               # D  Переходы
        f"=SUM(E2:E{last_data_row})",               # E  Корзины
        f"=SUM(F2:F{last_data_row})",               # F  Выкупы
        f"=SUM(G2:G{last_data_row})",               # G  Сумма продаж
        f"=SUM(H2:H{last_data_row})",               # H  Внутр. реклама
        f"=IF(C{total_row}=0,0,D{total_row}/C{total_row})",   # I  CTR
        f"=IF(D{total_row}=0,0,E{total_row}/D{total_row})",   # J  CR в корзину
        f"=IF(D{total_row}=0,0,F{total_row}/D{total_row})",   # K  CR в выкуп
        f"=IF(F{total_row}=0,0,G{total_row}/F{total_row})",   # L  Средний чек
        f"=IF(G{total_row}=0,0,H{total_row}/G{total_row})",   # M  ДРР
    ]
    ws.append_row(total_row_data, value_input_option="USER_ENTERED")

    # --- Formatting ---
    _apply_formatting(spreadsheet, ws, total_row)

    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit"
    logger.info("Spreadsheet ready: %s", sheet_url)
    return sheet_url


def _apply_formatting(
    spreadsheet: gspread.Spreadsheet,
    ws: gspread.Worksheet,
    total_row: int,
) -> None:
    """Apply visual formatting: freeze header, bold header + ИТОГО, percent formats."""
    spreadsheet_id = spreadsheet.id

    requests = [
        # Freeze the header row
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": ws.id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Bold header row (row index 0)
        {
            "repeatCell": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        },
        # Bold ИТОГО row (0-indexed = total_row - 1)
        {
            "repeatCell": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": total_row - 1,
                    "endRowIndex": total_row,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                    }
                },
                "fields": "userEnteredFormat.textFormat",
            }
        },
        # Percent format for columns I, J, K, M (indices 8, 9, 10, 12)
        *[
            {
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 1,
                        "endRowIndex": total_row,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "PERCENT",
                                "pattern": "0.00%",
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat",
                }
            }
            for col in (8, 9, 10, 12)  # I, J, K, M
        ],
        # Currency format for column G (index 6) and H (index 7)
        *[
            {
                "repeatCell": {
                    "range": {
                        "sheetId": ws.id,
                        "startRowIndex": 1,
                        "endRowIndex": total_row,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": "#,##0.00",
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat",
                }
            }
            for col in (6, 7, 11)  # G, H, L
        ],
        # Auto-resize all columns
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": ws.id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 13,
                }
            }
        },
    ]

    spreadsheet.batch_update({"requests": requests})
    logger.info("Formatting applied to spreadsheet %s", spreadsheet_id)
