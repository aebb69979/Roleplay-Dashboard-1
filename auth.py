"""
Lightweight passcode gate - not tied to Google/Azure identity. A single
dict of name -> passcode in secrets covers both "one shared password"
(one entry) and "individual codes" (many entries) with the same code.
"""
import base64
import time
from pathlib import Path

import streamlit as st

from branding import render_header

_BACKGROUND_IMAGE = Path(__file__).parent / "Image" / "login_background_2.webp"


@st.cache_data
def _background_data_uri() -> str:
    encoded = base64.b64encode(_BACKGROUND_IMAGE.read_bytes()).decode()
    return f"data:image/webp;base64,{encoded}"


def require_passcode() -> None:
    render_header()

    if st.session_state.get("authed"):
        return

    # .stApp is an undocumented internal hook (unlike the st-key-*
    # pattern used elsewhere in this app) - Streamlit's theme system has
    # no native support for a full-bleed background image, so this is
    # the only way to do it. May need updating if a future Streamlit
    # release changes this markup.
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{_background_data_uri()}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        div[class*="st-key-login-card-"] {{
            background-color: #FAF8F6;
            border-radius: 20px;
            padding: 2.5rem 2.75rem;
            border: 1px solid rgba(255, 255, 255, 0.4);
            box-shadow: 0 20px 60px rgba(15, 23, 42, 0.35);
            max-width: 440px;
            margin: 10vh auto 0 auto;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # A plain `with st.container(...)` here would leave a dimmed, stale
    # copy of the login card on screen for the whole time the dashboard
    # takes to load after a correct passcode - Streamlit only sweeps away
    # elements the new run didn't recreate once that new run finishes
    # entirely, not as soon as they're superseded. Routing the card
    # through a placeholder lets us clear it explicitly the moment the
    # passcode is accepted, before st.rerun() hands off to the dashboard
    # run.
    placeholder = st.empty()
    with placeholder.container(key="login-card-wrap"):
        st.title("Roleplay Training Dashboard")
        st.caption("Enter your passcode to continue.")

        with st.form("login"):
            passcode = st.text_input("Passcode", type="password")
            submitted = st.form_submit_button("Enter")

        if submitted:
            codes = dict(st.secrets.get("auth", {}).get("codes", {}))
            if passcode and passcode in codes.values():
                st.session_state["authed"] = True
                placeholder.empty()
                # st.rerun() aborts the script immediately, which can cut
                # off the .empty() delta before it reaches the frontend -
                # a confirmed Streamlit bug (streamlit/streamlit#14280,
                # #12069, #5044). This tiny pause gives it time to flush
                # first; without it the old card can flash back briefly,
                # especially when the dashboard's own cache is already
                # warm and the next run finishes almost instantly.
                time.sleep(0.15)
                st.rerun()
            else:
                st.error("Invalid passcode.")

    st.stop()
