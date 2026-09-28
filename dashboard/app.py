"""Interactive Streamlit dashboard for request-level LLM analytics."""
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from llm_analytics import by_dimension, clean_usage, load_usage_data, summarize

st.set_page_config(page_title="LLM Usage & Cost Analytics", page_icon="📊", layout="wide")
st.title("📊 LLM Usage & Cost Analytics")
st.caption("Request-level usage, estimated spend, latency, and reliability")

uploaded = st.sidebar.file_uploader("Upload a compatible CSV", type="csv")
if uploaded is not None:
    try:
        data = clean_usage(pd.read_csv(uploaded))
    except (ValueError, pd.errors.ParserError) as exc:
        st.error(f"Could not load the uploaded file: {exc}")
        st.stop()
else:
    data = load_usage_data(ROOT / "data" / "llm_usage.csv")

if data.empty:
    st.warning("No valid usage records found. Add a CSV with the documented schema.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    date_values = sorted(data["date"].unique())
    selected_dates = st.date_input("Date range", value=(date_values[0], date_values[-1]))
    if not isinstance(selected_dates, tuple):
        selected_dates = (selected_dates, selected_dates)
    applications = st.multiselect("Applications", sorted(data["application"].dropna().unique()), default=sorted(data["application"].dropna().unique()))
    models = st.multiselect("Models", sorted(data["model"].dropna().unique()), default=sorted(data["model"].dropna().unique()))
    statuses = st.multiselect("Statuses", sorted(data["status"].dropna().unique()), default=sorted(data["status"].dropna().unique()))

filtered = data[
    data["date"].between(selected_dates[0], selected_dates[-1])
    & data["application"].isin(applications)
    & data["model"].isin(models)
    & data["status"].isin(statuses)
]
if filtered.empty:
    st.info("No records match the current filters. Broaden the date or category selections.")
    st.stop()

metrics = summarize(filtered)
cols = st.columns(5)
cols[0].metric("Requests", f"{metrics['requests']:,}")
cols[1].metric("Estimated cost", f"${metrics['cost_usd']:,.2f}")
cols[2].metric("Total tokens", f"{metrics['tokens']:,}")
cols[3].metric("Success rate", f"{metrics['success_rate']:.1f}%")
cols[4].metric("P95 latency", f"{metrics['p95_latency_ms']:,.0f} ms")

left, right = st.columns(2)
with left:
    st.subheader("Daily estimated cost")
    daily = filtered.groupby("date", as_index=False)["cost_usd"].sum()
    st.line_chart(daily.set_index("date"), y="cost_usd")
with right:
    st.subheader("Cost by model")
    model_cost = by_dimension(filtered, "model")
    st.bar_chart(model_cost.set_index("model"), y="cost_usd")

left, right = st.columns(2)
with left:
    st.subheader("Latency distribution")
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(data=filtered, x="model", y="latency_ms", ax=ax)
    ax.tick_params(axis="x", rotation=25)
    ax.set_ylabel("Latency (ms)")
    st.pyplot(fig, clear_figure=True)
with right:
    st.subheader("Application scorecard")
    scorecard = by_dimension(filtered, "application")
    st.dataframe(scorecard.style.format({"cost_usd": "${:,.2f}", "avg_latency_ms": "{:,.0f}", "success_rate": "{:.1f}%"}), use_container_width=True, hide_index=True)

with st.expander("Filtered request data"):
    st.dataframe(filtered.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
