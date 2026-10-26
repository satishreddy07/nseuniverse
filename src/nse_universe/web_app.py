"""NSE Universe private live market dashboard."""
from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from nse_universe.providers.instrument_master import InstrumentMaster
from nse_universe.providers.kotak_neo import KotakNeoAdapter, NormalizedTick

st.set_page_config(page_title="NSE Universe | Intraday Terminal", page_icon="📈", layout="wide")
st.markdown("""<style>
.stApp{background:#080f19;color:#e6edf7}
[data-testid="stSidebar"]{background:#0b1421;border-right:1px solid #1b2b40}
.block-container{padding-top:1rem;max-width:1800px}
h1,h2,h3{letter-spacing:-.025em}
div[data-testid="stMetric"]{background:linear-gradient(145deg,#101c2b,#0c1623);border:1px solid #203249;border-radius:12px;padding:13px}
div[data-testid="stMetricLabel"]{color:#91a3bb}
div[data-testid="stMetricValue"]{color:#edf4ff}
div[data-testid="stDataFrame"]{border:1px solid #203249;border-radius:10px}
</style>""", unsafe_allow_html=True)

async def _collect(adapter, tokens, seconds, feed_type):
    received=[]
    async def consume():
        started=time.monotonic()
        async for tick in adapter.stream(tokens, feed_type=feed_type):
            received.append(tick)
            if time.monotonic()-started >= seconds:
                break
    try:
        await asyncio.wait_for(consume(), timeout=seconds)
    except asyncio.TimeoutError:
        pass
    return received

def collect_ticks(adapter, tokens, seconds, feed_type):
    return asyncio.run(_collect(adapter,tokens,seconds,feed_type))

with st.sidebar:
    st.markdown("## ▥ NSE Universe")
    st.caption("Nifty F&O · Market intelligence")
    page=st.radio("Workspace",["Dashboard","Live Market","Option Chain","OI Analysis","Order Flow","Settings"])
    st.divider()
    authenticated=bool(st.session_state.get("kotak_authenticated"))
    st.success("Kotak Neo session active" if authenticated else "Disconnected")
    st.caption("Market data only · No orders")
    if st.button("Log out",use_container_width=True):
        st.session_state.pop("kotak_adapter",None)
        st.session_state["kotak_authenticated"]=False
        st.session_state.pop("live_ticks",None)
        st.rerun()

st.caption("INTRADAY MARKET INTELLIGENCE")
st.title("Market Dashboard")
st.caption("Live broker data · freshness-aware analytics · analysis only")
adapter=st.session_state.get("kotak_adapter") if authenticated else None
if not adapter:
    st.warning("Authenticate with Kotak Neo to open the live dashboard.")
    st.stop()

master_path=st.text_input("Instrument master CSV",value="data/nse_fo.csv")
try:
    master=InstrumentMaster.from_csv(master_path)
except Exception as exc:
    st.error(f"Could not load instrument master ({type(exc).__name__}). Check the CSV path.")
    st.stop()

a,b,c,d=st.columns([2.2,1.1,1.1,1])
with a:
    query=st.text_input("Find instruments",value="NIFTY")
with b:
    found_segments=sorted({x.exchange_segment for x in master.search(query,limit=500)}) if query.strip() else []
    segment=st.selectbox("Segment",found_segments or ["nse_fo"])
with c:
    feed_type=st.selectbox("Feed",["touchline","depth","full_depth"])
with d:
    seconds=st.selectbox("Seconds",[5,10,15],index=1)
matches=master.search(query.strip(),exchange_segment=segment,limit=100) if query.strip() else ()
if not matches:
    st.warning("No symbols found. Search for NIFTY26NOVFUT or another exact symbol.")
    st.stop()
symbols=[x.trading_symbol for x in matches]
default=next((x for x in symbols if x.endswith("FUT") and "NIFTY" in x),symbols[0])
selected=st.multiselect("Subscriptions",symbols,default=[default])
left_button,right_note=st.columns([1,5])
with left_button:
    capture=st.button("▶ Capture live ticks",type="primary",use_container_width=True)
with right_note:
    st.caption(f"{len(master):,} instruments in master · {len(selected)} selected · 5-second freshness target")

if capture:
    if not selected:
        st.error("Select at least one symbol.")
    elif len(selected)>100:
        st.error("Select no more than 100 symbols for one capture.")
    else:
        instruments=[master.by_symbol(segment,s) for s in selected]
        tokens=[(i.exchange_segment,i.token) for i in instruments if i is not None]
        try:
            with st.spinner(f"Listening to Kotak Neo for {seconds} seconds…"):
                new=collect_ticks(adapter,tokens,float(seconds),feed_type)
            old=st.session_state.get("live_ticks",[])
            merged={(t.exchange_segment,t.instrument_token):t for t in old}
            for tick in new:
                merged[(tick.exchange_segment,tick.instrument_token)]=tick
            st.session_state["live_ticks"]=list(merged.values())
            st.session_state["last_capture_at"]=datetime.now(timezone.utc).isoformat()
            st.session_state["last_capture_count"]=len(new)
            if new:
                st.success(f"Received {len(new)} tick updates.")
            else:
                st.warning("No usable ticks arrived. Check market hours, symbols, and feed permissions.")
        except Exception as exc:
            st.error(f"Live feed capture failed ({type(exc).__name__}). Check the SDK and connection.")

ticks: list[NormalizedTick]=st.session_state.get("live_ticks",[])
latest={}
for tick in ticks:
    instrument=master.get(tick.exchange_segment,tick.instrument_token)
    symbol=instrument.trading_symbol if instrument else (tick.trading_symbol or tick.instrument_token)
    if symbol not in latest or tick.received_at>=latest[symbol].received_at:
        latest[symbol]=tick
now=datetime.now(timezone.utc)
fresh=[s for s in selected if s in latest and (now-latest[s].received_at).total_seconds()<=5]
primary=next((latest[s] for s in selected if s in latest),None)
m1,m2,m3,m4,m5=st.columns(5)
m1.metric("Selected instrument",primary.trading_symbol if primary and primary.trading_symbol else (selected[0] if selected else "—"))
m2.metric("Last traded price",f"{primary.last_traded_price:,.2f}" if primary else "—")
m3.metric("Open interest",f"{primary.open_interest:,.0f}" if primary and primary.open_interest is not None else "—")
m4.metric("Volume",f"{primary.volume:,.0f}" if primary and primary.volume is not None else "—")
m5.metric("Fresh subscriptions",f"{len(fresh)} / {len(selected)}")

lcol,rcol=st.columns([1.7,1])
with lcol:
    with st.container(border=True):
        st.subheader("Price monitor")
        rows=[]
        for tick in sorted(ticks,key=lambda x:x.received_at):
            instrument=master.get(tick.exchange_segment,tick.instrument_token)
            if instrument and instrument.trading_symbol in selected:
                rows.append({"Time (UTC)":tick.received_at,instrument.trading_symbol:tick.last_traded_price})
        if rows:
            st.line_chart(pd.DataFrame(rows).set_index("Time (UTC)"),height=280)
        else:
            st.info("Capture ticks to populate the chart.")
    with st.container(border=True):
        st.subheader("Live instrument tape")
        rows=[]
        for symbol in selected:
            item=next((x for x in matches if x.trading_symbol==symbol),None)
            tick=latest.get(symbol)
            age=(now-tick.received_at).total_seconds() if tick else None
            rows.append({"Symbol":symbol,"Token":item.token if item else "—","LTP":tick.last_traded_price if tick else None,"OI":tick.open_interest if tick else None,"Volume":tick.volume if tick else None,"Bid":tick.best_bid_price if tick else None,"Ask":tick.best_ask_price if tick else None,"Age (s)":round(age,1) if age is not None else None,"Status":"FRESH" if age is not None and age<=5 else ("STALE" if age is not None else "MISSING")})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
with rcol:
    with st.container(border=True):
        st.subheader("Connection health")
        st.write("Broker: Kotak Neo")
        st.write("Session: Authenticated")
        st.write(f"Last capture: {st.session_state.get('last_capture_at','Not run yet')}")
        st.write(f"Updates received: {st.session_state.get('last_capture_count',0)}")
        st.write("Freshness target: 5 seconds")
        st.progress(len(fresh)/max(len(selected),1))
        st.caption("Stale or missing data is explicitly flagged.")
    with st.container(border=True):
        st.subheader("PCR & market sentiment")
        st.metric("ATM / nearby / overall PCR","Awaiting option chain")
        st.caption("No synthetic PCR or sentiment values are displayed.")
    with st.container(border=True):
        st.subheader("Order flow & depth")
        if primary and (primary.total_buy_quantity is not None or primary.total_sell_quantity is not None):
            buy=primary.total_buy_quantity or 0
            sell=primary.total_sell_quantity or 0
            total=buy+sell
            share=100*buy/total if total else 0
            st.metric("Buy quantity share",f"{share:.1f}%")
            st.progress(share/100)
            st.caption(f"Buy {buy:,.0f} · Sell {sell:,.0f}")
        else:
            st.info("Choose depth feed to request available bid/ask and aggregate quantities.")
        if primary:
            st.dataframe(pd.DataFrame([{"Side":"Bid","Price":primary.best_bid_price,"Qty":primary.best_bid_quantity},{"Side":"Ask","Price":primary.best_ask_price,"Qty":primary.best_ask_quantity}]),use_container_width=True,hide_index=True)

with st.expander("Data notes and limitations"):
    st.markdown("This version uses bounded capture windows; click Capture live ticks to refresh. The chart plots received ticks, not reconstructed candles. PCR, option-chain heatmaps, VWAP, sector breadth, and trade-probability scores are not fabricated; they need the relevant validated data and analytics wiring. Keep the app private. No order-entry methods are exposed.")
st.caption("NSE Universe · Private dashboard · Analysis only")
