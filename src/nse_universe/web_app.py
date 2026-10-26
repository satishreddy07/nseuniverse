"""Local Streamlit login screen for Kotak Neo market-data access.

Credentials are used only in this server-side session and are not written to disk.
This page does not place orders.
"""
from __future__ import annotations

import streamlit as st

from nse_universe.providers.kotak_neo import KotakNeoAdapter, KotakNeoConfig

st.set_page_config(page_title="NSE Universe · Broker Login", page_icon="📈", layout="centered")

st.title("NSE Universe")
st.subheader("Kotak Neo connection")
st.warning(
    "Market-data access only. Credentials are used by this server session and are not "
    "saved to a file. Do not expose this page publicly or enter credentials on a "
    "shared/untrusted computer."
)

with st.form("kotak_login", clear_on_submit=True):
    consumer_key = st.text_input("Consumer key", type="password", autocomplete="off")
    mobile_number = st.text_input("Registered mobile number", autocomplete="off")
    ucc = st.text_input("Client/UCC", autocomplete="off")
    mpin = st.text_input("MPIN", type="password", autocomplete="off")
    environment = st.selectbox("Environment", options=["prod", "uat"], index=0)
    totp = st.text_input("Current TOTP", type="password", autocomplete="off")
    submitted = st.form_submit_button("Authenticate with Kotak Neo", type="primary")

if submitted:
    missing = [
        label for label, value in (
            ("Consumer key", consumer_key),
            ("Registered mobile number", mobile_number),
            ("Client/UCC", ucc),
            ("MPIN", mpin),
            ("Current TOTP", totp),
        ) if not value.strip()
    ]
    if missing:
        st.error("Please fill in: " + ", ".join(missing))
    else:
        try:
            config = KotakNeoConfig(
                consumer_key=consumer_key.strip(),
                mobile_number=mobile_number.strip(),
                ucc=ucc.strip(),
                mpin=mpin.strip(),
                environment=environment,
            )
            adapter = KotakNeoAdapter(config)
            with st.spinner("Authenticating with Kotak Neo…"):
                adapter.authenticate(totp=totp)
            # Keep the authenticated client in this server-side browser session only.
            st.session_state["kotak_adapter"] = adapter
            st.session_state["kotak_authenticated"] = True
            st.success("Authentication succeeded for this session.")
            st.caption("No orders are placed. Restarting the app or ending the session clears this session state.")
        except Exception as exc:
            st.session_state.pop("kotak_adapter", None)
            st.session_state["kotak_authenticated"] = False
            # Avoid displaying provider response bodies that might contain sensitive data.
            st.error(f"Authentication failed ({type(exc).__name__}). Check the details and current TOTP, then try again.")

if st.session_state.get("kotak_authenticated"):
    st.success("Status: authenticated")
else:
    st.caption("Status: not authenticated")

st.caption("This screen currently validates login only; live feed selection and dashboard are separate next steps.")
