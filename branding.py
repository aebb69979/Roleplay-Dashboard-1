"""
Shared chrome rendered on every page - the white header bar with the True
logo. A single call site (auth.py's require_passcode(), which every page
calls first) covers both the login screen and the authenticated dashboard.
"""
from pathlib import Path

import streamlit as st

_LOGO = Path(__file__).parent / "Image" / "true_logo_transparent.png"


def render_header() -> None:
    # st.logo is the native, documented way to place a logo in the
    # upper-left corner - this app has no sidebar, so it lands in the
    # app's own header bar instead. That header (data-testid="stHeader")
    # is already fixed at the top and stays put while the page scrolls,
    # so there's no need for a separate custom fixed div.
    st.logo(str(_LOGO), size="large")
    st.markdown(
        """
        <style>
        [data-testid="stHeader"] {
            background-color: #FFFFFF;
            border-bottom: 1px solid #E4E7EC;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
