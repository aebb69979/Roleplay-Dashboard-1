"""
Raw pulls from Google Drive/Sheets. Two different transports on purpose:
Responses lives as a native Google Sheet (Sheets API, cell-range read);
the Mapping workbook is an uploaded .xlsx (Drive file download + pandas).
"""
import io

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from data import schema as s

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

RESPONSES_SHEET_ID = st.secrets["ids"]["responses_sheet_id"]
MAPPING_FILE_ID = st.secrets["ids"]["mapping_file_id"]


def _credentials() -> Credentials:
    return Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )


@st.cache_resource
def _sheets_client() -> gspread.Client:
    return gspread.authorize(_credentials())


@st.cache_data(ttl=600)  # responses arrive continuously — refresh every 10 min
def fetch_responses() -> pd.DataFrame:
    ws = _sheets_client().open_by_key(RESPONSES_SHEET_ID).worksheet("Form Responses 1")
    values = ws.get_all_values()  # raw rows — do NOT trust the header row's text
    body = values[1:]
    df = pd.DataFrame(body, columns=s.RESPONSE_COLUMNS[: len(body[0])])
    return df


@st.cache_data(ttl=3600)  # roster changes rarely — hourly is plenty
def fetch_mapping(sheet_name: str = "Data") -> pd.DataFrame:
    drive = build("drive", "v3", credentials=_credentials())
    request = drive.files().get_media(fileId=MAPPING_FILE_ID)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return pd.read_excel(buf, sheet_name=sheet_name, engine="openpyxl")
