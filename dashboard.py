import streamlit as st
import pandas as pd
import duckdb
from datetime import datetime, timezone
import os

st.set_page_config(
    page_title="J/Z Train Performance",
    page_icon="🚇",
    layout="wide",
)


# ---------- Neon techno style ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@300;400;600&display=swap');

    html, body, .stApp {
        background-color: #080c10 !important;
        color: #c9d1d9;
        font-family: 'Inter', sans-serif;
    }

    h1 {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 2rem !important;
        color: #00ffe7 !important;
        text-shadow: 0 0 12px #00ffe7, 0 0 30px #00ffe780;
        letter-spacing: 0.05em;
        margin-bottom: 0 !important;
    }

    h2, h3 {
        font-family: 'Share Tech Mono', monospace !important;
        color: #ff2d78 !important;
        text-shadow: 0 0 8px #ff2d7860;
        letter-spacing: 0.04em;
        font-size: 1rem !important;
        text-transform: uppercase;
    }

    [data-testid="stMetric"] {
        background: #0d1520;
        border: 1px solid #00ffe720;
        border-radius: 4px;
        padding: 1rem;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 0.7rem !important;
        color: #8b949e !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Share Tech Mono', monospace !important;
        font-size: 1.8rem !important;
        color: #00ffe7 !important;
        text-shadow: 0 0 8px #00ffe760;
    }

    hr { border-color: #1c2940 !important; }

    [data-testid="stExpander"] {
        background: #0d1520 !important;
        border: 1px solid #1c2940 !important;
        border-radius: 4px;
    }

    .badge-red   { color: #ff2d78; font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; }
    .badge-amber { color: #ffb300; font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; }
    .badge-blue  { color: #00ffe7; font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; }

    .freshness-bar {
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.72rem;
        color: #3a4a5c;
        border-left: 2px solid #00ffe730;
        padding-left: 0.7rem;
        margin-bottom: 1rem;
        letter-spacing: 0.05em;
    }

    .pill-j {
        display: inline-block;
        background: #ff2d78;
        color: #fff;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 3px;
        margin-right: 0.4rem;
    }
    .pill-z {
        display: inline-block;
        background: #00ffe7;
        color: #080c10;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 3px;
        margin-right: 0.4rem;
    }

    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            #00ffe703 2px,
            #00ffe703 4px
        );
        pointer-events: none;
        z-index: 0;
    }
</style>
""", unsafe_allow_html=True)


# ---------- Load data ----------
@st.cache_data(ttl=300)
def load_features():
    try:
        con = duckdb.connect()
        con.execute(f"""
            SET s3_access_key_id='{os.environ["R2_ACCESS_KEY_ID"]}';
            SET s3_secret_access_key='{os.environ["R2_SECRET_ACCESS_KEY"]}';
            SET s3_endpoint='{os.environ["R2_ENDPOINT_HOSTNAME"]}';
            SET s3_url_style='path';
        """)
        df = con.execute("""
            SELECT * FROM read_parquet('s3://jz-pipeline/data/features/jz_combined/jz_features.parquet')
            ORDER BY window_start DESC
        """).fetchdf()
        con.close()
        return df
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return pd.DataFrame()
df = load_features()

# ---------- Header ----------
st.markdown("# 🚇 J/Z TRAIN PERFORMANCE")
st.caption("Real-time reliability vs. weather conditions — NYC MTA")

if df.empty:
    st.warning("No data found. Run `python flow.py` then `dbt run` to populate the warehouse.")
    st.stop()

latest = df.iloc[0]
newest = df["window_start"].max()

# ---------- Freshness bar ----------
st.markdown(
    f"""<div class="freshness-bar">
    TRANSIT: ~60s refresh &nbsp;&#9656;&nbsp; WEATHER: hourly &nbsp;&#9656;&nbsp;
    GRAIN: 15-min window &nbsp;&#9656;&nbsp; LAST RUN: {newest.strftime('%Y-%m-%d %H:%M UTC')}
    </div>""",
    unsafe_allow_html=True,
)

# ---------- Status row ----------
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    gap = latest['avg_headway_gap_sec']
    st.metric("AVG HEADWAY GAP", f"{int(gap//60)}m {int(gap%60)}s" if pd.notna(gap) else "—")
with col2:
    st.metric("MAX HEADWAY GAP", f"{int(latest['max_headway_gap_sec']//60)}m" if pd.notna(latest['max_headway_gap_sec']) else "—")
with col3:
    pct = latest.get('pct_delayed', None)
    st.metric("% DELAYED", f"{pct:.1f}%" if pd.notna(pct) else "—")
with col4:
    st.metric("ALERTS", f"{int(latest['alerts_active'])}")
with col5:
    temp = latest["temperature_c"]
    heat = " 🔥" if latest.get("is_extreme_heat") else ""
    st.metric("TEMP", f"{temp:.1f}°C{heat}" if pd.notna(temp) else "—")
with col6:
    precip = latest["precip_mm"]
    rain = " 🌧" if latest.get("is_precip") else ""
    st.metric("PRECIP", f"{precip:.1f}mm{rain}" if pd.notna(precip) else "—")

st.divider()

# ---------- Charts ----------
left, right = st.columns([2, 1])

with left:
    st.subheader("Headway gap vs. temperature")
    chart_df = (
        df.set_index("window_start")[["avg_headway_gap_sec", "temperature_c"]]
        .dropna(how="all")
        .sort_index()
    )
    st.line_chart(chart_df, color=["#00ffe7", "#ff2d78"])

with right:
    st.subheader("Delay severity breakdown")
    if all(c in df.columns for c in ["severe_count", "moderate_count", "minor_count", "on_time_count"]):
        sev_df = df[["window_start", "on_time_count", "minor_count", "moderate_count", "severe_count"]]\
            .set_index("window_start").tail(20).sort_index()
        st.bar_chart(sev_df, color=["#00ffe7", "#ffb300", "#ff6b35", "#ff2d78"])
    else:
        st.info("No severity breakdown yet.")

st.divider()

# ---------- Active alerts ----------
# ---------- Alerts ----------
try:
    con = duckdb.connect()
    con.execute(f"""
        SET s3_access_key_id='{os.environ["R2_ACCESS_KEY_ID"]}';
        SET s3_secret_access_key='{os.environ["R2_SECRET_ACCESS_KEY"]}';
        SET s3_endpoint='{os.environ["R2_ENDPOINT_HOSTNAME"]}';
        SET s3_url_style='path';
    """)
    ongoing = con.execute("""
        SELECT route_id, header, hours_since_start
        FROM (
            SELECT
                unnest(route_ids) as route_id,
                header,
                start_time,
                end_time,
                extract(epoch from (now() - start_time::TIMESTAMPTZ)) / 3600 as hours_since_start,
                case
                    when start_time::TIMESTAMPTZ > now() then 'upcoming'
                    when end_time is null then 'ongoing'
                    when end_time::TIMESTAMPTZ > now() then 'active'
                    else 'expired'
                end as alert_status
            FROM read_parquet('s3://jz-pipeline/data/processed/alerts/*.parquet')
            WHERE end_time IS NULL OR end_time::BIGINT > epoch(now())
        )
        WHERE alert_status = 'ongoing'
        AND route_id IN ('J', 'Z')
        QUALIFY row_number() OVER (PARTITION BY route_id, header ORDER BY hours_since_start DESC) = 1
        ORDER BY hours_since_start DESC
    """).fetchdf()

    upcoming = con.execute("""
        SELECT route_id, header, hours_until_start, start_time, end_time
        FROM (
            SELECT
                unnest(route_ids) as route_id,
                header,
                start_time,
                end_time,
                extract(epoch from (start_time::TIMESTAMPTZ - now())) / 3600 as hours_until_start,
                case
                    when start_time::BIGINT > epoch(now()) then 'upcoming'
                    else 'other'
                end as alert_status
            FROM read_parquet('s3://jz-pipeline/data/processed/alerts/*.parquet')
        )
        WHERE alert_status = 'upcoming'
        AND route_id IN ('J', 'Z')
        QUALIFY row_number() OVER (PARTITION BY route_id, header ORDER BY hours_until_start ASC) = 1
        ORDER BY hours_until_start ASC
    """).fetchdf()

except Exception as e:
    st.error(f"Alert query failed: {e}")
    ongoing = pd.DataFrame()
    upcoming = pd.DataFrame()
finally:
    con.close()
    
    
    
# Ongoing disruptions
st.subheader("Ongoing disruptions")
if ongoing.empty:
    st.info("No active disruptions.")
else:
    for _, row in ongoing.iterrows():
        pill = "pill-j" if row["route_id"] == "J" else "pill-z"
        days = int(row["hours_since_start"] // 24)
        hours = int(row["hours_since_start"] % 24)
        duration = f"{days}d {hours}h" if days > 0 else f"{hours}h"
        with st.expander(f"🔴  [{row['route_id']}]  {str(row['header'])[:80]}..."):
            st.markdown(
                f'<span class="{pill}">{row["route_id"]}</span>'
                f'<span class="badge-red">[ ONGOING — {duration} ]</span>',
                unsafe_allow_html=True,
            )
            st.write(row["header"])

st.write("")

# Upcoming planned work
st.subheader("Upcoming planned work")
if upcoming.empty:
    st.info("No planned work scheduled.")
else:
    for _, row in upcoming.iterrows():
        pill = "pill-j" if row["route_id"] == "J" else "pill-z"
        hours = int(row["hours_until_start"])
        days = hours // 24
        eta = f"in {days}d {hours % 24}h" if days > 0 else f"in {hours}h"
        start = pd.to_datetime(row["start_time"]).strftime("%b %d %H:%M UTC")
        end = pd.to_datetime(row["end_time"]).strftime("%b %d %H:%M UTC") if pd.notna(row["end_time"]) else "TBD"
        with st.expander(f"🟡  [{row['route_id']}]  {str(row['header'])[:80]}..."):
            st.markdown(
                f'<span class="{pill}">{row["route_id"]}</span>'
                f'<span class="badge-amber">[ PLANNED — starts {eta} ]</span>',
                unsafe_allow_html=True,
            )
            st.write(f"**From:** {start}")
            st.write(f"**Until:** {end}")
            st.write(row["header"])
# ---------- Extreme weather callout ----------
st.subheader("Extreme heat windows")
extreme = df[df["is_extreme_heat"] == True]
if extreme.empty:
    st.info("No extreme heat windows (>=32.2C / 90F) recorded yet.")
else:
    st.dataframe(
        extreme[[
            "window_start", "route_id", "avg_delay_sec",
            "temperature_c", "alerts_active", "pct_delayed"
        ]],
        use_container_width=True,
    )

st.divider()

# ---------- Raw table ----------
with st.expander("Raw feature table"):
    st.dataframe(df, use_container_width=True)

# ---------- Footer ----------
st.markdown(
    """<div class="freshness-bar" style="margin-top:2rem">
    Occupancy approximated from headway gaps — MTA does not publish per-train occupancy.
    &nbsp;&#9656;&nbsp; Weather: Open-Meteo &nbsp;&#9656;&nbsp; Transit: MTA GTFS-RT
    </div>""",
    unsafe_allow_html=True,
)