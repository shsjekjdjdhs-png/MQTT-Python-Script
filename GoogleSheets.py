"""
GoogleSheets.py - reusable Google Sheets append helper, shared by every collector.

One Google Cloud service account (see .env: GOOGLE_SHEETS_CREDENTIALS_FILE) is
reused for ALL spreadsheets. Each spreadsheet is a separate customer/sensor
destination, looked up by a short name from GOOGLE_SHEETS_IDS in .env.

============================================================
HOW TO ADD A NEW CUSTOMER / SENSOR SPREADSHEET (no code change needed)
============================================================
1. Create a new Google Sheet for that customer/sensor.
2. Share it with the service account email (Editor access) - find the
   email in credentials/google_sheets_service_account.json, field
   "client_email". It is the SAME service account for every spreadsheet.
3. Copy the spreadsheet ID from its URL:
       https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
4. Add one line to .env under GOOGLE_SHEETS_IDS, e.g.:
       GOOGLE_SHEETS_IDS="Bin_Sensor2=1Nj3Fno...,CustomerA_Beacon1=1AbCdE..."
   (comma-separated "<short_name>=<spreadsheet_id>" pairs, no spaces)
5. In the new collector script:
       from GoogleSheets import append_row
       append_row(row, "CustomerA_Beacon1", "Beacon1", header=[...])
   - the 2nd argument is the short_name from step 4 (which spreadsheet)
   - the 3rd argument is the worksheet/tab name inside that spreadsheet
     (auto-created on first use, along with the header row if given)
============================================================

Connects once per spreadsheet, at first use, and reuses the same
worksheet handle for every append_row() call afterward - reconnecting
per insert would be wasteful, since each connection has real
network/auth overhead.

Usage:

    from GoogleSheets import append_row

    append_row(["2026-09-18T10:00:00", "12", 45.2], "Bin_Sensor2", "Bin_Sensor2")
"""
import logging
import os

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _parse_spreadsheet_ids(raw):
    # "name1=id1,name2=id2" -> {"name1": "id1", "name2": "id2"}
    ids = {}
    for pair in (raw or "").split(","):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        name, spreadsheet_id = pair.split("=", 1)
        ids[name.strip()] = spreadsheet_id.strip()
    return ids


SPREADSHEET_IDS = _parse_spreadsheet_ids(os.getenv("GOOGLE_SHEETS_IDS"))

_client = None
_spreadsheets = {}  # short_name -> gspread.Spreadsheet, cached after first open
_worksheets = {}  # (short_name, worksheet_name) -> gspread.Worksheet, cached after first lookup/creation

try:
    _credentials = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=SCOPES)
    _client = gspread.authorize(_credentials)
    logging.info("Google Sheets service account authorized")
except Exception as e:
    logging.error(f"Could not authorize Google Sheets service account: {e}")


def _get_spreadsheet(short_name):
    if short_name in _spreadsheets:
        return _spreadsheets[short_name]

    spreadsheet_id = SPREADSHEET_IDS.get(short_name)
    if spreadsheet_id is None:
        raise KeyError(
            f"no spreadsheet configured for '{short_name}' - add it to GOOGLE_SHEETS_IDS in .env "
            "(see the how-to at the top of GoogleSheets.py)"
        )

    spreadsheet = _client.open_by_key(spreadsheet_id)
    logging.info(f"Connected to Google Sheet '{spreadsheet.title}' ({short_name})")
    _spreadsheets[short_name] = spreadsheet
    return spreadsheet


def _get_worksheet(short_name, worksheet_name, header=None):
    cache_key = (short_name, worksheet_name)
    if cache_key in _worksheets:
        return _worksheets[cache_key]

    spreadsheet = _get_spreadsheet(short_name)
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        num_cols = max(len(header or []), 10)
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=num_cols)
        if header:
            worksheet.append_row(header)
        _apply_default_formatting(worksheet, num_cols)

    _worksheets[cache_key] = worksheet
    return worksheet


def _apply_default_formatting(worksheet, num_cols):
    # bold header row, center-align every column (including future rows,
    # since this is applied at the column level, not just the header range)
    last_col = gspread.utils.rowcol_to_a1(1, num_cols).rstrip("0123456789")
    try:
        worksheet.format(f"A1:{last_col}1", {"textFormat": {"bold": True}})
        worksheet.format(f"A:{last_col}", {"horizontalAlignment": "CENTER"})
    except Exception as e:
        logging.error(f"failed to apply default formatting to worksheet '{worksheet.title}': {e}")


def append_row(values, short_name, worksheet_name="Sheet1", header=None):
    """Append one row to a worksheet in a configured spreadsheet.

    short_name is the spreadsheet's key from GOOGLE_SHEETS_IDS in .env
    (which customer/sensor spreadsheet). worksheet_name is the tab within
    it. header, if given, is written as the first row the first time the
    worksheet is created - ignored on later calls.
    """
    if _client is None:
        raise RuntimeError("Google Sheets client is not authorized")

    worksheet = _get_worksheet(short_name, worksheet_name, header)
    worksheet.append_row(values, value_input_option="USER_ENTERED")
