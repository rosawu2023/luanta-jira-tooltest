import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Plotly: make it explicit if missing
try:
    import plotly.express as px
except ModuleNotFoundError:
    px = None

# ----------------------------
# Helpers
# ----------------------------
def pick_col(df: pd.DataFrame, candidates: list[str]):
    """Pick the first existing column name from candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    return None

def coerce_datetime(df: pd.DataFrame, col: str):
    if col and col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    return df

def normalize_percent_to_numeric(series: pd.Series) -> pd.Series:
    # Handles "12.3%", " 12.3 ", None
    s = series.astype(str).str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(s, errors="coerce")

def try_read_default_csv():
    """Try loading v1 first, then fallback to v0."""
    base_dir = Path(__file__).resolve().parent
    v1 = base_dir / "Luanta_Final_Demo_Data_v1.csv"
    v0 = base_dir / "Luanta_Final_Demo_Data.csv"
    if v1.exists():
        return pd.read_csv(v1), str(v1.name)
    if v0.exists():
        return pd.read_csv(v0), str(v0.name)
    raise FileNotFoundError("No default CSV found in repo root.")

def safe_metric(label, value):
    st.metric(label, "N/A" if value is None else value)

# ----------------------------
# Page
# ----------------------------
st.set_page_config(page_title="Luanta Jira Analytics", layout="wide")
st.title("📊 Luanta Service Performance Dashboard")

with st.expander("Debug info", expanded=False):
    st.write("Python:", sys.version)
    st.write("Pandas:", pd.__version__)
    st.write("Plotly installed:", px is not None)

if px is None:
    st.warning("Plotly is not installed. Charts will be disabled until you add `plotly` into requirements.txt.")

# ----------------------------
# Sidebar Upload
# ----------------------------
st.sidebar.header("Step 1: Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload Jira CSV", type="csv")

df = None
source_name = None

if uploaded_file is None:
    try:
        df, source_name = try_read_default_csv()
        st.info(f"💡 正在讀取預設範例數據：`{source_name}`（你也可以在側邊欄上傳新檔）")
    except Exception as e:
        st.error("找不到預設 CSV，請上傳檔案。")
        st.exception(e)
        st.stop()
else:
    try:
        df = pd.read_csv(uploaded_file)
        source_name = uploaded_file.name
        st.success(f"✅ 已成功讀取上傳檔案：{source_name}")
    except Exception as e:
        st.error("讀取上傳 CSV 失敗，請確認檔案格式。")
        st.exception(e)
        st.stop()

# ----------------------------
# Column Mapping (support v0/v1 + flexible names)
# ----------------------------
created_col = pick_col(df, ["Created_Date", "Created", "Created Date", "Created_Date (日期)"])
updated_col = pick_col(df, ["Last_Updated_Date", "Updated", "Updated Date", "Last Updated", "Last_Updated"])
resolved_col = pick_col(df, ["Resolved_Date", "Resolved", "Resolution Date", "Done Date"])
status_col  = pick_col(df, ["Status_Current", "Status", "status"])
status_entered_col = pick_col(df, ["Status_Entered_Date", "Status Entered Date", "Status_Entered"])
role_col    = pick_col(df, ["Role", "Team", "Component Owner"])
assignee_col = pick_col(df, ["Assignee", "Owner"])
priority_col = pick_col(df, ["Priority"])
reopen_col  = pick_col(df, ["Re_open_Count", "Reopen Count", "Reopen"])
delay_col   = pick_col(df, ["Delay_Rate", "Delay_Rate_%", "Delay Rate", "Delay Rate (%)", "Delay%"])
estimate_col = pick_col(df, ["Estimate_Hrs", "Estimate Hours"])
actual_col  = pick_col(df, ["Actual_Hrs", "Actual Hours"])
sla_hours_col = pick_col(df, ["SLA_Hours", "SLA Hours"])
sla_breach_col = pick_col(df, ["SLA_Breached", "SLA Breached"])
root_cause_col = pick_col(df, ["Root_Cause_Category", "Root Cause", "Root_Cause"])
blocked_reason_col = pick_col(df, ["Blocked_Reason", "Blocked Reason"])
handoff_col = pick_col(df, ["Handoff_Count", "Handoff Count"])

# Time coercion
df = coerce_datetime(df, created_col)
df = coerce_datetime(df, updated_col)
df = coerce_datetime(df, resolved_col)
df = coerce_datetime(df, status_entered_col)

# Normalize delay to numeric
if delay_col is not None:
    df[delay_col] = normalize_percent_to_numeric(df[delay_col])

# Preview
with st.expander("Data preview (first 20 rows)", expanded=False):
    st.write("Detected columns:")
    st.write({
        "created": created_col, "updated": updated_col, "resolved": resolved_col,
        "status": status_col, "status_entered": status_entered_col,
        "role": role_col, "assignee": assignee_col, "priority": priority_col,
        "delay": delay_col, "reopen": reopen_col, "estimate": estimate_col, "actual": actual_col,
        "sla_hours": sla_hours_col, "sla_breached": sla_breach_col,
        "root_cause": root_cause_col, "blocked_reason": blocked_reason_col,
        "handoff": handoff_col
    })
    st.dataframe(df.head(20), use_container_width=True)

# ----------------------------
# Base Metrics (works even for v0)
# ----------------------------
st.subheader("Key Metrics")

total_tkt = len(df)

p0_count = None
if priority_col:
    p0_count = int((df[priority_col] == "P0-Critical").sum())

avg_delay = None
if delay_col:
    avg_delay = df[delay_col].mean()

m1, m2, m3 = st.columns(3)
m1.metric("Total Tickets", total_tkt)
m2.metric("P0 Critical Issues", p0_count if p0_count is not None else "N/A")
m3.metric("Avg. Delay Rate", f"{avg_delay:.1f}%" if pd.notna(avg_delay) else "N/A")

# ----------------------------
# Delay by Role (if available)
# ----------------------------
st.subheader("Performance Breakdown")

if px is None:
    st.info("Charts are disabled because Plotly is missing.")
else:
    if role_col and delay_col:
        role_delay = df.groupby(role_col, dropna=False)[delay_col].mean().reset_index()
        role_delay[role_col] = role_delay[role_col].fillna("Unknown")

        fig = px.bar(
            role_delay, x=role_col, y=delay_col, color=role_col,
            labels={delay_col: "Delay Rate (%)"},
            title="Average Delay by Team Role"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("缺少 Role 或 Delay 欄位，已略過角色延遲圖表。")

# ----------------------------
# Workflow Finder (v1 features; gracefully degrade)
# ----------------------------
st.subheader("Workflow Finder")

c1, c2 = st.columns(2)

# WIP by Status
with c1:
    if status_col:
        st.markdown("**WIP by Status**")
        wip = df[status_col].fillna("Unknown").value_counts().reset_index()
        wip.columns = ["Status", "Count"]
        if px:
            fig = px.bar(wip, x="Status", y="Count", title="Current Work In Progress by Status")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(wip, use_container_width=True)
    else:
        st.info("缺少 Status 欄位，已略過 WIP 分析。")

# Queue time (how long in current status)
with c2:
    if status_col and status_entered_col:
        st.markdown("**Queue Time (days) by Status**")
        now = pd.Timestamp.utcnow()
        df["_queue_days"] = (now - df[status_entered_col]).dt.total_seconds() / 86400
        queue = df.groupby(status_col, dropna=False)["_queue_days"].mean().sort_values(ascending=False).reset_index()
        queue[status_col] = queue[status_col].fillna("Unknown")
        if px:
            fig = px.bar(queue, x=status_col, y="_queue_days", title="Average Queue Time by Status (days)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(queue, use_container_width=True)
    else:
        st.info("缺少 Status_Entered_Date 或 Status 欄位，已略過 Queue Time 分析。")

# Stale tickets (long time since last update)
if updated_col:
    st.markdown("**Stale Tickets (no update)**")
    now = pd.Timestamp.utcnow()
    df["_stale_days"] = (now - df[updated_col]).dt.total_seconds() / 86400
    top_stale = df.sort_values("_stale_days", ascending=False).head(15)

    show_cols = []
    for c in [pick_col(df, ["Issue_Key", "Issue key", "Key", "Issue_Key (卡片編號)"]),
              pick_col(df, ["Summary", "Summary (任務內容)"]),
              priority_col, role_col, status_col, updated_col, "_stale_days"]:
        if c and c in top_stale.columns:
            show_cols.append(c)

    st.dataframe(top_stale[show_cols], use_container_width=True)
else:
    st.info("缺少 Last_Updated_Date（或 Updated）欄位，已略過 Stale tickets 分析。")

# SLA section
if sla_breach_col or (created_col and resolved_col and sla_hours_col):
    st.subheader("SLA / Risk")

    # If SLA_Breached exists, use it
    if sla_breach_col:
        breach_rate = (df[sla_breach_col].astype(str).str.upper() == "Y").mean() * 100
        st.write(f"**SLA Breach Rate:** {breach_rate:.1f}%")
        if priority_col:
            by_pri = df.groupby(priority_col, dropna=False)[sla_breach_col].apply(lambda s: (s.astype(str).str.upper()=="Y").mean()*100).sort_values(ascending=False)
            st.dataframe(by_pri.reset_index().rename(columns={sla_breach_col: "Breach Rate (%)"}), use_container_width=True)
    else:
        # Compute breach from lead time and SLA_Hours
        lead = (df[resolved_col] - df[created_col]).dt.total_seconds()/3600
        breach = lead > df[sla_hours_col]
        st.write(f"**SLA Breach Rate (computed):** {(breach.mean()*100):.1f}%")

else:
    st.info("缺少 SLA 欄位（SLA_Breached / SLA_Hours），已略過 SLA 分析。")

# Root cause section
if root_cause_col:
    st.subheader("Root Cause Breakdown")
    rc = df[root_cause_col].fillna("Unknown").value_counts().reset_index()
    rc.columns = ["Root_Cause", "Count"]
    if px:
        fig = px.pie(rc, names="Root_Cause", values="Count", title="Root Cause Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(rc, use_container_width=True)

# Blocked section
if status_col and blocked_reason_col:
    st.subheader("Blocked Details")
    blocked_df = df[df[status_col].astype(str).str.lower() == "blocked"].copy()
    if len(blocked_df) == 0:
        st.write("目前沒有 Blocked tickets。")
    else:
        st.write(f"Blocked tickets: **{len(blocked_df)}**")
        cols = []
        for c in [pick_col(df, ["Issue_Key", "Issue_Key (卡片編號)"]), pick_col(df, ["Summary", "Summary (任務內容)"]),
                  priority_col, role_col, assignee_col, blocked_reason_col]:
            if c and c in blocked_df.columns:
                cols.append(c)
        st.dataframe(blocked_df[cols], use_container_width=True)

# ----------------------------
# Executive Report (works with whatever is available)
# ----------------------------
if st.button("Generate Executive Report"):
    st.subheader("📋 Executive Summary")

    bullets = []

    # Bottleneck by delay
    if role_col and delay_col:
        role_delay = df.groupby(role_col)[delay_col].mean().sort_values(ascending=False)
        top_role = role_delay.index[0]
        top_val = role_delay.iloc[0]
        bullets.append(f"- **Delay Bottleneck:** `{top_role}` has the highest average delay (**{top_val:.1f}%**).")

    # Queue bottleneck
    if status_col and status_entered_col:
        now = pd.Timestamp.utcnow()
        qdays = (now - df[status_entered_col]).dt.total_seconds()/86400
        q_by_status = qdays.groupby(df[status_col].fillna("Unknown")).mean().sort_values(ascending=False)
        bullets.append(f"- **Queue Bottleneck:** `{q_by_status.index[0]}` has the longest average queue time (**{q_by_status.iloc[0]:.1f} days**).")

    # SLA risk
    if sla_breach_col:
        breach_rate = (df[sla_breach_col].astype(str).str.upper() == "Y").mean() * 100
        bullets.append(f"- **SLA Risk:** Breach rate is **{breach_rate:.1f}%**.")

    # Root cause
    if root_cause_col:
        top_rc = df[root_cause_col].fillna("Unknown").value_counts().index[0]
        bullets.append(f"- **Primary Root Cause:** `{top_rc}` is the most frequent category.")

    if not bullets:
        bullets.append("- Not enough structured columns to generate a full executive summary. Consider using the v1 CSV schema.")

    st.markdown("\n".join(bullets))
