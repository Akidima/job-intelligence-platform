#!/usr/bin/env python3
"""Streamlit dashboard for the Job Intelligence Platform."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from src.storage.models import init_db, get_session_local, Job, Company, Skill, ExecutionLog
from src.skills.extractor import SkillExtractor
from src.analytics.engine import AnalyticsEngine

st.set_page_config(
    page_title="Job Intelligence Platform",
    page_icon=" ",
    layout="wide",
)

st.title("  Global Job Intelligence Platform")
st.caption("Real-time analytics for entry-level analytics positions worldwide")


@st.cache_resource
def init():
    init_db()
    return get_session_local()


def load_jobs():
    session_factory = init()
    session = session_factory()
    jobs = session.query(Job).filter(Job.is_active == True, Job.is_duplicate == False).all()
    data = []
    for job in jobs:
        data.append({
            "id": job.id,
            "title": job.title,
            "company": job.company.name if job.company else "Unknown",
            "country": job.country or "Remote",
            "city": job.city or "",
            "remote_type": job.remote_type or "unknown",
            "experience_level": job.experience_level or "Entry-Level",
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "visa_sponsorship": job.visa_sponsorship,
            "source": job.source,
            "posting_date": job.posting_date,
            "url": job.url,
        })
    session.close()
    return pd.DataFrame(data)


def load_execution_logs():
    session_factory = init()
    session = session_factory()
    logs = session.query(ExecutionLog).order_by(ExecutionLog.started_at.desc()).limit(10).all()
    data = [
        {
            "run_id": log.run_id,
            "status": log.status,
            "jobs_found": log.jobs_found,
            "jobs_validated": log.jobs_validated,
            "started_at": log.started_at,
        }
        for log in logs
    ]
    session.close()
    return pd.DataFrame(data)


# Sidebar
st.sidebar.header("Filters")

df = load_jobs()

if df.empty:
    st.warning("No jobs found. Run the pipeline first: `python main.py`")
    st.stop()

# Filters
countries = ["All"] + sorted(df["country"].unique().tolist())
selected_country = st.sidebar.selectbox("Country", countries)

sources = ["All"] + sorted(df["source"].unique().tolist())
selected_source = st.sidebar.selectbox("Source", sources)

remote_options = ["All", "remote", "hybrid", "onsite"]
selected_remote = st.sidebar.selectbox("Remote Type", remote_options)

# Apply filters
filtered = df.copy()
if selected_country != "All":
    filtered = filtered[filtered["country"] == selected_country]
if selected_source != "All":
    filtered = filtered[filtered["source"] == selected_source]
if selected_remote != "All":
    filtered = filtered[filtered["remote_type"] == selected_remote]

# Main metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Jobs", len(filtered))
col2.metric("Companies", filtered["company"].nunique())
col3.metric("Countries", filtered["country"].nunique())
col4.metric(
    "Visa Sponsorship",
    int(filtered["visa_sponsorship"].sum()) if "visa_sponsorship" in filtered else 0,
)

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "  Job Listings", "  Skills Analytics",
    "  Geographic Distribution", "  Execution Logs"
])

with tab1:
    st.subheader("Job Listings")
    display_cols = ["title", "company", "country", "remote_type", "experience_level", "source"]
    if "visa_sponsorship" in filtered:
        display_cols.append("visa_sponsorship")

    st.dataframe(
        filtered[display_cols].head(100),
        use_container_width=True,
        column_config={
            "visa_sponsorship": st.column_config.CheckboxColumn("Visa"),
        },
    )

    # Download
    csv = filtered.to_csv(index=False)
    st.download_button("Download CSV", csv, "jobs.csv", "text/csv")

with tab2:
    st.subheader("Skills Analytics")
    extractor = SkillExtractor()

    all_text = " ".join(
        f"{row.get('title', '')} " for _, row in filtered.iterrows()
    )
    skills = extractor.extract_skills(all_text)

    if skills:
        skill_df = pd.DataFrame(skills[:20])
        fig = px.bar(
            skill_df, x="name", y="count",
            title="Top Skills in Job Listings",
            color="category",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No skills extracted yet")

with tab3:
    st.subheader("Geographic Distribution")

    country_counts = filtered["country"].value_counts().head(15).reset_index()
    country_counts.columns = ["country", "count"]

    fig = px.bar(
        country_counts, x="country", y="count",
        title="Jobs by Country",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Remote vs Onsite
    remote_counts = filtered["remote_type"].value_counts().reset_index()
    remote_counts.columns = ["type", "count"]
    fig2 = px.pie(
        remote_counts, values="count", names="type",
        title="Remote vs Onsite vs Hybrid",
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab4:
    st.subheader("Execution Logs")
    logs_df = load_execution_logs()
    if not logs_df.empty:
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("No execution logs yet")
