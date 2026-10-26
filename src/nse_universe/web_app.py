"""NSE Universe broker login."""
import streamlit as st
from nse_universe.providers.kotak_neo import KotakNeoAdapter, KotakNeoConfig
st.set_page_config(page_title="NSE Universe Login",page_icon="📈",layout="centered")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
.stApp{background:radial-gradient(ellipse at 50% 0%,#152b49 0%,#080d16 55%);color:#e9f1fc;font-family:'Manrope',sans-serif}
[data-testid="stHeader"]{background:transparent}
.block-container{max-width:760px;padding-top:5vh;padding-bottom:4rem}
h1,h2,h3{color:#f2f7ff!important;letter-spacing:-.04em!important;font-family:'Manrope',sans-serif!important}
h1{font-size:2.7rem!important;font-weight:800!important}
h2{font-size:1.35rem!important;font-weight:750!important}
p,[data-testid="stCaptionContainer"]{color:#9db0c8}
[data-testid="stForm"]{background:linear-gradient(145deg,#101d2e,#0b1421);border:1px solid #2a3d56;border-radius:20px;padding:1.5rem;box-shadow:0 22px 70px #00000040}
[data-testid="stTextInput"] input,[data-testid="stSelectbox"]>div>div{background:#0a1422!important;border-color:#2a405c!important;border-radius:10px!important;color:#eef5ff!important}
[data-testid="stTextInput"] label,[data-testid="stSelectbox"] label{color:#a8bad0;font-weight:700;font-size:.82rem}
.stButton>button[kind="primary"]{background:linear-gradient(100deg,#2677e8,#439bff);border:0;border-radius:11px;color:white;font-weight:800;min-height:2.8rem;box-shadow:0 6px 22px #2477e833}
[data-testid="stAlert"]{border-radius:12px}
</style>""",unsafe_allow_html=True)

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
