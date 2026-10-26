"""NSE Universe broker login."""
import streamlit as st
from nse_universe.providers.kotak_neo import KotakNeoAdapter, KotakNeoConfig
st.set_page_config(page_title="NSE Universe Login",page_icon="📈",layout="centered")
st.title("NSE Universe")
st.subheader("Connect Kotak Neo")
st.warning("Keep this local app private. Login details are used for this session and are not saved to disk.")
with st.form("login",clear_on_submit=True):
    key=st.text_input("Consumer key",type="password")
    mobile=st.text_input("Registered mobile number")
    ucc=st.text_input("Client / UCC")
    pin=st.text_input("MPIN",type="password")
    env=st.selectbox("Environment",["prod","uat"])
    code=st.text_input("Current TOTP",type="password")
    go=st.form_submit_button("Authenticate",type="primary")
if go:
    try:
        cfg=KotakNeoConfig(consumer_key=key.strip(),mobile_number=mobile.strip(),ucc=ucc.strip(),mpin=pin.strip(),environment=env)
        client=KotakNeoAdapter(cfg)
        client.authenticate(totp=code)
        st.session_state["kotak_adapter"]=client
        st.session_state["kotak_authenticated"]=True
        st.success("Authenticated. Use the Dashboard page in the sidebar.")
    except Exception as exc:
        st.session_state["kotak_authenticated"]=False
        st.error("Authentication failed ("+type(exc).__name__+"). Verify inputs and TOTP.")
if st.session_state.get("kotak_authenticated"):
    st.success("Session authenticated")
else:
    st.caption("Not authenticated")
