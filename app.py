import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Luanta Jira Analytics", layout="wide")
st.title("📊 Luanta Service Performance Dashboard")

# Debug: show python version (helps verify runtime.txt is applied)
with st.expander("Debug info", expanded=False):
    st.write("Python:", sys.version)
    st.write("Pandas:", pd.__version__)

# ----------------------------
# Sidebar: upload
# ----------------------------
st.sidebar.header("Step 1: Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload Jira CSV", type="csv")

# ----------------------------
# Load data
# ----------------------------
df = None

def load_default_csv():
    """
    Load the default CSV shipped with the repo.
    Uses robust path resolution for Streamlit Cloud.
    """
    base_dir = Path(__file__).resolve().parent
    default_path = base_dir / "Luanta_Final_Demo_Data.csv"
    return pd.read_csv(default_path)

if uploaded_file is None:
    try:
        df = load_default_csv()
        st.info("💡 正在讀取預設範例數據。您也可以在上傳區丟入新檔案。")
    except Exception as e:
        st.warning("請在側邊欄上傳您的 Jira CSV 檔案以開始分析。")
        with st.expander("Debug: default CSV load error", expanded=False):
            st.exception(e)
        df = None
else:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ 已成功讀取上傳檔案。")
    except Exception as e:
        st.error("讀取上傳 CSV 失敗，請確認檔案格式。")
        st.exception(e)
        df = None

# If no data, stop here.
if df is None:
    st.stop()

# ----------------------------
# Column detection & validation
# ----------------------------

# 1) Detect Delay column (contains 'Delay')
delay_cols = [c for c in df.columns if "Delay" in str(c)]
if not delay_cols:
    st.error(
        "找不到包含 **'Delay'** 的欄位。\n\n"
        "請確認你的 CSV 有 Delay 相關欄位（例如：`Delay Rate (%)`、`Delay%`、`Delay Rate`）。"
    )
    with st.expander("Debug: columns", expanded=False):
        st.write(list(df.columns))
    st.stop()

delay_col = delay_cols[0]

# 2) Role column required for chart + report
if "Role" not in df.columns:
    st.error(
        "找不到 **'Role'** 欄位。\n\n"
        "請確認你的 CSV 有 Role 欄位（例如：Backend / Frontend / QA / PM）。"
    )
    with st.expander("Debug: columns", expanded=False):
        st.write(list(df.columns))
    st.stop()

# 3) Normalize Delay column to numeric (handle '12.3%' / '12.3' / empty)
df[delay_col] = (
    df[delay_col]
    .astype(str)
    .str.replace("%", "", regex=False)
    .str.strip()
)
df[delay_col] = pd.to_numeric(df[delay_col], errors="coerce")

# Optional: show a small preview for sanity
with st.expander("Data preview", expanded=False):
    st.write("Detected delay column:", delay_col)
    st.dataframe(df.head(20), use_container_width=True)

# ----------------------------
# Metrics
# ----------------------------
total_tkt = len(df)

if "Priority" in df.columns:
    p0_count = len(df[df["Priority"] == "P0-Critical"])
else:
    p0_count = "N/A"

avg_delay = df[delay_col].mean()

m1, m2, m3 = st.columns(3)
m1.metric("Total Tickets", total_tkt)
m2.metric("P0 Critical Issues", p0_count)
m3.metric("Avg. Delay Rate", f"{avg_delay:.1f}%" if pd.notna(avg_delay) else "N/A")

# ----------------------------
# Charts
# ----------------------------
st.subheader("Performance Breakdown")

# groupby Role
role_delay = df.groupby("Role", dropna=False)[delay_col].mean().reset_index()

# If Role has NaN, show as "Unknown"
role_delay["Role"] = role_delay["Role"].fillna("Unknown")

fig = px.bar(
    role_delay,
    x="Role",
    y=delay_col,
    color="Role",
    labels={delay_col: "Delay Rate (%)"},
    title="Average Delay by Team Role"
)
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Executive report
# ----------------------------
if st.button("Generate Executive Report"):
    st.subheader("📋 Executive Summary")

    # Backend rate (only if "Backend" exists; otherwise fallback)
    if (df["Role"] == "Backend").any():
        backend_rate = df.loc[df["Role"] == "Backend", delay_col].mean()
        bottleneck_text = f"Backend team shows **{backend_rate:.1f}%** delay." if pd.notna(backend_rate) else "Backend delay is not available."
    else:
        # pick max role as bottleneck
        max_row = role_delay.sort_values(by=delay_col, ascending=False).head(1)
        if len(max_row) == 1 and pd.notna(max_row.iloc[0][delay_col]):
            bottleneck_role = str(max_row.iloc[0]["Role"])
            bottleneck_val = float(max_row.iloc[0][delay_col])
            bottleneck_text = f"Highest delay is **{bottleneck_role}** with **{bottleneck_val:.1f}%**."
        else:
            bottleneck_text = "Cannot determine bottleneck due to missing delay data."

    # risk level heuristic (simple)
    risk_level = "High" if pd.notna(avg_delay) and avg_delay >= 20 else ("Medium" if pd.notna(avg_delay) and avg_delay >= 10 else "Low")

    st.markdown(f"""
- **Core Bottleneck:** {bottleneck_text}
- **Risk Level:** {risk_level}
- **Action Plan:** Establish clear API specifications with MG HQ to reduce back-and-forth communication.
    """)
