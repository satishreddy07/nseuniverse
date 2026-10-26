"""NSE Universe modern live-market dashboard page."""
from __future__ import annotations
import asyncio, time
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from nse_universe.providers.instrument_master import InstrumentMaster
from nse_universe.providers.kotak_neo import NormalizedTick

st.set_page_config(page_title="NSE Universe Dashboard",page_icon="📈",layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--bg:#080d16;--panel:#0e1725;--panel2:#111e30;--line:#23334a;--muted:#8ea2bb;--text:#e9f1fc;--blue:#5aa7ff;--green:#32d49a;--red:#ff6d7b}
.stApp{background:radial-gradient(ellipse at 15% 0%,#10213a 0%,#080d16 42%);color:var(--text);font-family:'Manrope',sans-serif}
[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"]{right:1rem}
[data-testid="stSidebar"]{background:#0a111d;border-right:1px solid #1c2b40}
[data-testid="stSidebar"] > div:first-child{padding-top:1.4rem}
.block-container{padding:1.4rem 2.1rem 3rem;max-width:1800px}
h1,h2,h3{font-family:'Manrope',sans-serif!important;letter-spacing:-.035em!important;color:#f1f6ff!important}
h1{font-size:2.15rem!important;font-weight:800!important;margin:.1rem 0 .2rem!important}
h2{font-size:1.18rem!important;font-weight:750!important}
h3{font-size:1rem!important;font-weight:700!important}
p,[data-testid="stCaptionContainer"]{color:var(--muted)}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(18,31,49,.96),rgba(11,20,33,.96));border:1px solid #263952;border-radius:15px;padding:16px 18px;min-height:112px;box-shadow:0 8px 28px #00000014}
[data-testid="stMetricLabel"]{color:#9db0c8!important;font-size:.76rem!important;font-weight:700!important;text-transform:uppercase;letter-spacing:.075em}
[data-testid="stMetricValue"]{color:#f2f7ff!important;font-family:'DM Mono',monospace!important;font-size:1.55rem!important;font-weight:500}
[data-testid="stMetricDelta"]{font-family:'DM Mono',monospace}
[data-testid="stVerticalBlockBorderWrapper"]{background:linear-gradient(145deg,rgba(15,25,40,.94),rgba(10,17,29,.94));border:1px solid #22334a!important;border-radius:17px!important;padding:18px!important;box-shadow:0 12px 32px #00000012}
[data-testid="stDataFrame"]{border:1px solid #263952;border-radius:12px;overflow:hidden}
[data-testid="stTextInput"] input,[data-testid="stSelectbox"]>div>div,[data-testid="stMultiSelect"]>div>div{background:#0b1523!important;border-color:#293d57!important;border-radius:10px!important;color:#eaf2ff!important}
[data-testid="stTextInput"] label,[data-testid="stSelectbox"] label,[data-testid="stMultiSelect"] label{font-weight:700;font-size:.78rem;color:#a8bad0}
.stButton>button{border-radius:10px;border:1px solid #304965;font-weight:750;min-height:2.6rem;transition:all .15s ease}
.stButton>button[kind="primary"]{background:linear-gradient(100deg,#2677e8,#439bff);border:0;color:white;box-shadow:0 5px 18px #2477e833}
.stButton>button:hover{border-color:#65adff;transform:translateY(-1px)}
[data-testid="stAlert"]{border-radius:12px}
hr{border-color:#23334a}
small{color:var(--muted)}
div[data-testid="stProgressBar"]>div>div{background:linear-gradient(90deg,#398dff,#35d5a0)}
@media(max-width:900px){.block-container{padding:1rem .8rem 2rem}h1{font-size:1.7rem!important}[data-testid="stMetricValue"]{font-size:1.15rem!important}}
</style>""",unsafe_allow_html=True)
async def collect(adapter,tokens,seconds,feed_type):
    ticks=[]
    async def consume():
        started=time.monotonic()
        async for tick in adapter.stream(tokens,feed_type=feed_type):
            ticks.append(tick)
            if time.monotonic()-started>=seconds: break
    try: await asyncio.wait_for(consume(),timeout=seconds)
    except asyncio.TimeoutError: pass
    return ticks

st.caption("NSE UNIVERSE / INTRADAY MARKET INTELLIGENCE")
st.title("Market Dashboard")
st.caption("Live broker data · freshness-aware analytics · analysis only")
adapter=st.session_state.get("kotak_adapter") if st.session_state.get("kotak_authenticated") else None
if adapter is None:
    st.warning("Authenticate from the NSE Universe Login page first.")
    st.stop()
master_path=st.text_input("Instrument master CSV",value="data/nse_fo.csv")
try: master=InstrumentMaster.from_csv(master_path)
except Exception as exc:
    st.error(f"Instrument master load failed ({type(exc).__name__}).")
    st.stop()
a,b,c,d=st.columns([2.2,1.1,1.1,1])
with a: query=st.text_input("Find instruments",value="NIFTY")
with b:
    segs=sorted({i.exchange_segment for i in master.search(query,limit=500)}) if query.strip() else []
    segment=st.selectbox("Segment",segs or ["nse_fo"])
with c: feed=st.selectbox("Feed",["touchline","depth","full_depth"])
with d: seconds=st.selectbox("Window (s)",[5,10,15],index=1)
matches=master.search(query.strip(),exchange_segment=segment,limit=100) if query.strip() else ()
if not matches:
    st.info("Search a trading symbol such as NIFTY26NOVFUT.")
    st.stop()
symbols=[i.trading_symbol for i in matches]
default=next((s for s in symbols if s.endswith("FUT") and "NIFTY" in s),symbols[0])
selected=st.multiselect("Subscriptions",symbols,default=[default])
x,y=st.columns([1,5])
with x: run=st.button("▶ Capture live ticks",type="primary",use_container_width=True)
with y: st.caption(f"{len(master):,} instruments loaded · {len(selected)} selected · freshness threshold 5 seconds")
if run:
    if not selected: st.error("Select one or more instruments.")
    elif len(selected)>100: st.error("Select at most 100 instruments per capture.")
    else:
        chosen=[master.by_symbol(segment,s) for s in selected]
        try:
            with st.spinner(f"Listening for {seconds} seconds…"):
                new=asyncio.run(collect(adapter,[(i.exchange_segment,i.token) for i in chosen if i],float(seconds),feed))
            previous=st.session_state.get("live_ticks",[])
            merged={(t.exchange_segment,t.instrument_token):t for t in previous}
            for tick in new: merged[(tick.exchange_segment,tick.instrument_token)]=tick
            st.session_state["live_ticks"]=list(merged.values())
            st.session_state["last_capture_at"]=datetime.now(timezone.utc).isoformat()
            st.session_state["last_capture_count"]=len(new)
            if new: st.success(f"Received {len(new)} tick updates.")
            else: st.warning("No ticks received. Check market hours, symbol selection, and feed permissions.")
        except Exception as exc: st.error(f"Feed capture failed ({type(exc).__name__}): {str(exc)[:400]}")
ticks: list[NormalizedTick]=st.session_state.get("live_ticks",[])
latest={}
for tick in ticks:
    inst=master.get(tick.exchange_segment,tick.instrument_token)
    symbol=inst.trading_symbol if inst else (tick.trading_symbol or tick.instrument_token)
    if symbol not in latest or tick.received_at>=latest[symbol].received_at: latest[symbol]=tick
now=datetime.now(timezone.utc)
fresh=[s for s in selected if s in latest and (now-latest[s].received_at).total_seconds()<=5]
primary=next((latest[s] for s in selected if s in latest),None)
m1,m2,m3,m4,m5=st.columns(5)
m1.metric("Instrument",primary.trading_symbol if primary and primary.trading_symbol else (selected[0] if selected else "—"))
m2.metric("Last price",f"{primary.last_traded_price:,.2f}" if primary else "—")
m3.metric("Open interest",f"{primary.open_interest:,.0f}" if primary and primary.open_interest is not None else "—")
m4.metric("Volume",f"{primary.volume:,.0f}" if primary and primary.volume is not None else "—")
m5.metric("Fresh subscriptions",f"{len(fresh)} / {len(selected)}")
left,right=st.columns([1.7,1])
with left:
    with st.container(border=True):
        st.subheader("Price monitor")
        chart=[]
        for tick in sorted(ticks,key=lambda t:t.received_at):
            inst=master.get(tick.exchange_segment,tick.instrument_token)
            if inst and inst.trading_symbol in selected: chart.append({"Time (UTC)":tick.received_at,inst.trading_symbol:tick.last_traded_price})
        if chart: st.line_chart(pd.DataFrame(chart).set_index("Time (UTC)"),height=280)
        else: st.info("Capture live ticks to populate the chart.")
    with st.container(border=True):
        st.subheader("Live instrument tape")
        rows=[]
        for symbol in selected:
            inst=next((i for i in matches if i.trading_symbol==symbol),None); tick=latest.get(symbol)
            age=(now-tick.received_at).total_seconds() if tick else None
            rows.append({"Symbol":symbol,"Token":inst.token if inst else "—","LTP":tick.last_traded_price if tick else None,"OI":tick.open_interest if tick else None,"Volume":tick.volume if tick else None,"Bid":tick.best_bid_price if tick else None,"Ask":tick.best_ask_price if tick else None,"Age (s)":round(age,1) if age is not None else None,"Status":"FRESH" if age is not None and age<=5 else ("STALE" if age is not None else "MISSING")})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
with right:
    with st.container(border=True):
        st.subheader("Connection health")
        st.write("Broker: Kotak Neo"); st.write("Session: Authenticated")
        st.write("Last capture: "+str(st.session_state.get("last_capture_at","Not run yet")))
        st.write("Updates received: "+str(st.session_state.get("last_capture_count",0)))
        st.progress(len(fresh)/max(len(selected),1))
        st.caption("Stale and missing quotes are flagged.")
    with st.container(border=True):
        st.subheader("PCR & sentiment")
        st.metric("ATM / nearby / overall PCR","Awaiting option chain")
        st.caption("No synthetic analytics values are displayed.")
    with st.container(border=True):
        st.subheader("Order flow & depth")
        if primary and (primary.total_buy_quantity is not None or primary.total_sell_quantity is not None):
            buy=primary.total_buy_quantity or 0; sell=primary.total_sell_quantity or 0; total=buy+sell
            share=100*buy/total if total else 0
            st.metric("Buy quantity share",f"{share:.1f}%"); st.progress(share/100)
            st.caption(f"Buy {buy:,.0f} · Sell {sell:,.0f}")
        else: st.info("Choose depth feed to show available bid/ask and aggregate quantities.")
        if primary: st.dataframe(pd.DataFrame([{"Side":"Bid","Price":primary.best_bid_price,"Qty":primary.best_bid_quantity},{"Side":"Ask","Price":primary.best_ask_price,"Qty":primary.best_ask_quantity}]),use_container_width=True,hide_index=True)
with st.expander("Data notes and limitations"):
    st.write("This version uses bounded capture windows; click Capture live ticks to refresh. The chart plots received ticks, not reconstructed candles. PCR, option-chain heatmaps, VWAP, sector breadth and probability scores are not fabricated and need validated inputs. Keep the app private. No orders are placed.")
