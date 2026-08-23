"""
Lightweight passcode gate - not tied to Google/Azure identity. A single
dict of name -> passcode in secrets covers both "one shared password"
(one entry) and "individual codes" (many entries) with the same code.
"""
import streamlit as st


def require_passcode() -> None:
    if st.session_state.get("authed"):
        return

    st.title("Roleplay Training Dashboard")
    st.caption("Enter your passcode to continue.")

    with st.form("login"):
        passcode = st.text_input("Passcode", type="password")
        submitted = st.form_submit_button("Enter")

    if submitted:
        codes = dict(st.secrets.get("auth", {}).get("codes", {}))
        if passcode and passcode in codes.values():
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Invalid passcode.")

    st.stop()
