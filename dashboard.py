import streamlit as st
import pandas as pd
import duckdb
from datetime import datetime, timezone

st.set_page_config(
    page_title="J/Z Train Performance",
    page_icon="🚇",
    layout="wide",
)

WAREHOUSE_PATH = "warehouse/dev.duckdb"

# ---------- Style ----------
st.markdown("""
<style>
    .stApp { background-color: #0d1117; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    .freshness-note {
        font-size: 0.8rem;
        color: #8b949e;
        border-left: 3px solid #30363d;
        padding-left: 0.6rem;
        margin-top: -0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Load data ----------
@st.cache_data(ttl=60)
def load_features():
    try:
        con = duckdb.connect(WAREHOUSE_PATH, read_only=True)
        df = con.execute("""
            SELECT * FROM fct_jz_performance
            ORDER BY window_start DESC
        """).fetchdf()
        con.close()
        return df
    except Exception as e:
        st.error(f"Failed to load from warehouse: {e}")
        return pd.DataFrame()

df = load_features()

# ---------- Header ----------
st.title("🚇 J/Z Train Performance Monitor")
st.caption("How does weather impact subway reliability on the J/Z line?")

if df.empty:
    st.warning(
        "No feature data found yet. Run the pipeline (`python flow.py`) "
        "to generate `jz_features.parquet`."
    )
    st.stop()

latest = df.iloc[-1]
oldest = df["window_start"].min()
newest = df["window_start"].max()

# ---------- Freshness / meta info (US-03) ----------
st.markdown(
    f"""<div class="freshness-note">
    Transit feed: refreshed every ~60s &nbsp;|&nbsp; Weather feed: refreshed hourly &nbsp;|&nbsp;
    Data joined at a 15-minute window grain &nbsp;|&nbsp;
    Last updated: {newest.strftime('%Y-%m-%d %H:%M UTC')}
    </div>""",
    unsafe_allow_html=True,
)
st.write("")

# ---------- Current status row ----------
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Avg delay (latest)", f"{latest['avg_delay_sec']:.0f}s")
with col2:
    st.metric("Max delay (latest)", f"{latest['max_delay_sec']:.0f}s")
with col3:
    st.metric("Active alerts", f"{int(latest['alerts_active'])}")
with col4:
    temp = latest["temperature_c"]
    st.metric("Temperature", f"{temp:.1f}°C" if pd.notna(temp) else "—")
with col5:
    precip = latest["precip_mm"]
    st.metric("Precipitation", f"{precip:.1f}mm" if pd.notna(precip) else "—")

st.divider()

# ---------- Trend charts ----------
left, right = st.columns([2, 1])

with left:
    st.subheader("Delay vs. weather over time")
    chart_df = df.set_index("window_start")[["avg_delay_sec", "temperature_c"]].dropna(how="all")
    st.line_chart(chart_df)

with right:
    st.subheader("Delay severity mix")
    if "delay_records" in df.columns:
        st.bar_chart(df.set_index("window_start")[["delay_records"]].tail(20))
    else:
        st.info("No delay severity breakdown available yet.")

st.divider()

# ---------- Weather threshold callouts (US-01) ----------
st.subheader("Extreme weather days")
extreme = df[df["is_extreme_heat"] == True]
if extreme.empty:
    st.info("No extreme heat (≥90°F / 32.2°C) windows recorded yet.")
else:
    st.dataframe(
        extreme[["window_start", "avg_delay_sec", "temperature_c", "alerts_active"]],
        use_container_width=True,
    )

st.divider()

# ---------- Raw feature table ----------
with st.expander("View raw feature table"):
    st.dataframe(df, use_container_width=True)

# ---------- Disclaimer ----------
st.caption(
    "Occupancy is not directly reported by MTA and is approximated from headway gaps "
    "between trains. Weather data sourced from Open-Meteo; transit data from MTA GTFS-RT."
)