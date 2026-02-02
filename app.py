import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timezone

# =========================
# Page config
# =========================
st.set_page_config(page_title="Luanta Service Dashboard", layout="wide")

# =========================
# Global CSS (Dashboard cards + unified typography)
# =========================
st.markdown(
    """
<style>
.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1200px; }
section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }

/* Section card */
.section-card {
  border: 1px solid rgba(49, 51, 63, 0.14);
  background: #ffffff;
  border-radius: 16px;
  padding: 18px 18px 14px 18px;
  margin: 16px 0 18px 0;
  box-shadow: 0 6px 20px rgba(0,0,0,0.06);
}

/* Remove any visual dividers */
.soft-divider { display: none !important; }

/* Typography hierarchy */
.section-title { font-size: 1.40rem; font-weight: 780; margin: 0 0 0.15rem 0; }
.section-subtitle { font-size: 0.95rem; opacity: 0.72; margin: 0 0 0.85rem 0; }

.kpi-title { font-size: 1.10rem; font-weight: 760; margin: 0.2rem 0 0.2rem 0; }
.kpi-sub { font-size: 0.90rem; opacity: 0.72; margin: 0 0 0.55rem 0; }

.chart-title { font-size: 1.08rem; font-weight: 760; margin: 0.70rem 0 0.10rem 0; }
.chart-desc { font-size: 0.90rem; opacity: 0.72; margin: 0 0 0.60rem 0; }

.note {
  border-left: 4px solid rgba(0, 123, 255, 0.55);
  padding: 10px 12px;
  background: rgba(0, 123, 255, 0.06);
  border-radius: 12px;
  margin: 8px 0 10px 0;
}

.empty {
  border-left: 4px solid rgba(255, 193, 7, 0.75);
  padding: 10px 12px;
  background: rgba(255, 193, 7, 0.12);
  border-radius: 12px;
  margin: 8px 0 10px 0;
}

.small-muted { font-size: 0.85rem; opacity: 0.70; }

/* Make Streamlit metric look more dashboard-like */
[data-testid="stMetric"] {
  border: 1px solid rgba(49, 51, 63, 0.12);
  border-radius: 14px;
  padding: 10px 12px;
  background: #fff;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# Language utilities
# =========================
def tx(en: str, zh: str) -> str:
    return zh if st.session_state.get("lang", "zh") == "zh" else en

def card_title(en_title: str, zh_title: str, en_sub: str = "", zh_sub: str = ""):
    st.markdown(
        f"<div class='section-title'>{tx(en_title, zh_title)}</div>",
        unsafe_allow_html=True,
    )
    if (en_sub or zh_sub):
        st.markdown(
            f"<div class='section-subtitle'>{tx(en_sub, zh_sub)}</div>",
            unsafe_allow_html=True,
        )

def note(en_text: str, zh_text: str):
    st.markdown(
        f"<div class='note'>{tx(en_text, zh_text)}</div>",
        unsafe_allow_html=True,
    )

def empty_state(en_text: str, zh_text: str, tips=None):
    st.markdown(
        f"<div class='empty'>{tx(en_text, zh_text)}</div>",
        unsafe_allow_html=True,
    )
    if tips:
        st.markdown("<div class='small-muted'>", unsafe_allow_html=True)
        for t in tips:
            st.write("• " + t)
        st.markdown("</div>", unsafe_allow_html=True)

def to_datetime_safe(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", utc=True)

def render_chart_or_empty(df_plot: pd.DataFrame, chart_fn, empty_en: str, empty_zh: str, tips=None):
    if df_plot is None or df_plot.empty:
        empty_state(empty_en, empty_zh, tips=tips)
        return
    fig = chart_fn(df_plot)
    st.plotly_chart(fig, use_container_width=True)

# =========================
# Sidebar - upload + language toggle
# =========================
st.sidebar.header("設定 / Settings")
lang = st.sidebar.radio(
    "介面語言 / Language",
    options=["中文", "English"],
    index=0,
)
st.session_state["lang"] = "zh" if lang == "中文" else "en"

st.sidebar.header(tx("Step 1 Upload Data", "步驟一 上傳資料"))
uploaded_file = st.sidebar.file_uploader(tx("Upload Jira CSV", "上傳 Jira CSV"), type="csv")

# =========================
# Load data
# =========================
df = None
loaded_from = None

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        loaded_from = uploaded_file.name
        st.success(tx(f"Loaded uploaded file: {loaded_from}", f"已成功讀取上傳檔案：{loaded_from}"))
    except Exception as e:
        df = None
        st.error(tx("Failed to read the uploaded CSV.", "無法讀取你上傳的 CSV。"))
        st.exception(e)
else:
    # Default: try v1 first, then fallback
    for fname in ["Luanta_Final_Demo_Data_v1.csv", "Luanta_Final_Demo_Data.csv"]:
        try:
            df = pd.read_csv(fname)
            loaded_from = fname
            st.info(tx(f"Using default demo data: {fname}", f"目前使用預設範例資料：{fname}"))
            break
        except Exception:
            df = None

if df is None:
    st.warning(tx("Please upload a Jira CSV in the sidebar to start.", "請在左側上傳 Jira CSV 才能開始分析。"))
    st.stop()

# =========================
# Column detection (robust)
# =========================
def find_col(candidates):
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    # fuzzy: contains
    for c in df.columns:
        for cand in candidates:
            if cand.lower() in c.lower():
                return c
    return None

created_col = find_col(["Created_Date", "Created Date"])
issue_key_col = find_col(["Issue_Key", "Issue Key", "Key"])
summary_col = find_col(["Summary", "Task", "Title"])
role_col = find_col(["Role", "Team", "Assignee_Role"])
priority_col = find_col(["Priority"])
estimate_col = find_col(["Estimate_Hrs", "Estimate Hours", "Original Estimate"])
actual_col = find_col(["Actual_Hrs", "Actual Hours", "Time Spent"])
reopen_col = find_col(["Re_open_Count", "Reopen Count", "Reopen"])
delay_col = find_col(["Delay_Rate_%", "Delay Rate", "Delay"])
status_col = find_col(["Status_Current", "Status", "Current Status"])
status_entered_col = find_col(["Status_Entered_Date", "Status Entered", "Entered Date"])
last_updated_col = find_col(["Last_Updated_Date", "Updated", "Updated Date"])
assignee_col = find_col(["Assignee", "Owner"])
blocked_reason_col = find_col(["Blocked_Reason", "Block Reason", "Blocked Reason"])
root_cause_col = find_col(["Root_Cause", "Root Cause", "Category"])

# =========================
# Header
# =========================
st.markdown(
    f"<div class='section-card'>"
    f"<div class='section-title'>🏁 {tx('Luanta Service Performance Dashboard', 'Luanta 服務效能儀表板')}</div>"
    f"<div class='section-subtitle'>{tx('Upload a Jira export CSV to find bottlenecks and risks.', '上傳 Jira 匯出 CSV，協助找出流程卡點與風險。')}</div>"
    f"<div class='small-muted'>{tx('Data source', '資料來源')}：{loaded_from}</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# =========================
# Data preview (to address: "csv has many columns but only show some")
# =========================
with st.expander(tx("Debug info and data preview", "除錯資訊與資料預覽")):
    st.write(tx("Detected columns used in analysis:", "系統偵測到並用於分析的欄位："))
    detected = {
        "created_col": created_col,
        "issue_key_col": issue_key_col,
        "summary_col": summary_col,
        "role_col": role_col,
        "priority_col": priority_col,
        "estimate_col": estimate_col,
        "actual_col": actual_col,
        "reopen_col": reopen_col,
        "delay_col": delay_col,
        "status_col": status_col,
        "status_entered_col": status_entered_col,
        "last_updated_col": last_updated_col,
        "assignee_col": assignee_col,
        "blocked_reason_col": blocked_reason_col,
        "root_cause_col": root_cause_col,
    }
    st.json(detected)
    st.write(tx("First 20 rows:", "前 20 筆資料："))
    st.dataframe(df.head(20), use_container_width=True)
    st.write(tx("All columns in the CSV:", "CSV 全部欄位："))
    st.write(list(df.columns))

# =========================
# SECTION: Key Metrics
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Key Metrics",
    "關鍵指標",
    "High-level snapshot of ticket volume and delay.",
    "快速掌握工單量與延誤狀況。",
)

total_tickets = len(df)

# P0 definition (robust)
p0_count = "N/A"
if priority_col and priority_col in df.columns:
    p0_count = int(df[priority_col].astype(str).str.contains("P0", case=False, na=False).sum())

avg_delay = "N/A"
if delay_col and delay_col in df.columns:
    try:
        avg_delay_val = pd.to_numeric(df[delay_col], errors="coerce").mean()
        if pd.notna(avg_delay_val):
            avg_delay = f"{avg_delay_val:.1f}%"
    except Exception:
        pass

m1, m2, m3 = st.columns(3)
m1.metric(tx("Total Tickets", "工單總數"), total_tickets)
m2.metric(tx("P0 Critical Issues", "P0 高風險工單"), p0_count)
m3.metric(tx("Average Delay Rate", "平均延誤率"), avg_delay)

note(
    "Why some columns are not shown: each section only displays fields relevant to its analysis.",
    "為何只顯示部分欄位：每個區塊只會呈現該分析需要的欄位，避免把整份 CSV 全部塞上來造成閱讀負擔。",
)

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SECTION: Performance Breakdown
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Performance Breakdown",
    "效能拆解",
    "Compare delay across roles and identify hotspots.",
    "比較不同角色的延誤程度，定位熱區。",
)

if not (role_col and delay_col and role_col in df.columns and delay_col in df.columns):
    empty_state(
        "Not enough data to compute delay by role.",
        "資料不足以計算各角色的延誤。",
        tips=[
            tx("Missing Role or Delay column.", "缺少 Role 或 Delay 欄位。"),
            tx("Check your CSV export mapping.", "請確認匯出 CSV 的欄位是否符合。"),
        ],
    )
else:
    tmp = df[[role_col, delay_col]].copy()
    tmp[delay_col] = pd.to_numeric(tmp[delay_col], errors="coerce")
    role_delay = tmp.dropna().groupby(role_col, as_index=False)[delay_col].mean().sort_values(delay_col, ascending=False)

    st.markdown(f"<div class='chart-title'>{tx('Average Delay by Role', '各角色平均延誤')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-desc'>{tx('Higher means more overrun relative to estimate.', '數值越高代表越容易超出預估工時。')}</div>", unsafe_allow_html=True)

    render_chart_or_empty(
        role_delay,
        chart_fn=lambda d: px.bar(
            d, x=role_col, y=delay_col, color=role_col,
            title=tx("Average Delay by Team Role", "各角色平均延誤率"),
            labels={delay_col: tx("Delay Rate", "延誤率")}
        ),
        empty_en="No usable delay data found.",
        empty_zh="目前沒有可用的延誤資料可以顯示。",
        tips=[
            tx("Delay column must be numeric.", "Delay 欄位需要是數字。"),
            tx("If values contain symbols, remove them in export.", "如果含有符號，請在匯出時移除或在程式轉換。"),
        ],
    )

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SECTION: Workflow Finder
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Workflow Finder",
    "工作流程分析",
    "Use WIP and queue time to locate where work gets stuck.",
    "用在手量與等待時間找出流程卡點。",
)

note(
    "How to read: WIP shows volume. Queue time shows waiting. Long queue time often means dependency, unclear next action, or overloaded intake.",
    "如何解讀：在手量代表堆積的數量。等待時間代表卡多久。等待時間長通常意味外部依賴、缺少明確下一步、或前段排程塞住。",
)

c1, c2 = st.columns(2)

# WIP by Status
with c1:
    st.markdown(f"<div class='chart-title'>{tx('WIP by Status','各狀態在手量')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-desc'>{tx('Ticket count in each status.', '各狀態目前有多少工單。')}</div>", unsafe_allow_html=True)

    if not (status_col and status_col in df.columns):
        empty_state(
            "Not enough data to show WIP by status.",
            "資料不足以顯示各狀態在手量。",
            tips=[
                tx("Missing Status_Current column.", "缺少 Status_Current 欄位。"),
            ],
        )
    else:
        wip_df = df[status_col].dropna().astype(str).value_counts().rename_axis("Status").reset_index(name="Count")
        render_chart_or_empty(
            wip_df,
            chart_fn=lambda d: px.bar(
                d, x="Status", y="Count",
                title=tx("Current Work In Progress by Status", "各狀態在手量")
            ),
            empty_en="No usable status values found.",
            empty_zh="目前沒有可用的狀態資料可以顯示。",
            tips=[
                tx("Check if status values exist in the CSV.", "請確認狀態欄位在 CSV 內有值。"),
            ],
        )

# Queue time by Status
with c2:
    st.markdown(f"<div class='chart-title'>{tx('Queue Time by Status','各狀態等待時間')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chart-desc'>{tx('Average days tickets have stayed in each status.', '工單在每個狀態平均停留幾天。')}</div>", unsafe_allow_html=True)

    q_df = pd.DataFrame()
    if status_col and status_entered_col and status_col in df.columns and status_entered_col in df.columns:
        tmp = df[[status_col, status_entered_col]].copy()
        tmp[status_entered_col] = to_datetime_safe(tmp[status_entered_col])
        now_utc = pd.Timestamp.now(tz=timezone.utc)
        tmp["_queue_days"] = (now_utc - tmp[status_entered_col]).dt.total_seconds() / 86400.0
        tmp = tmp.dropna(subset=[status_col, "_queue_days"])
        q_df = tmp.groupby(status_col, as_index=False)["_queue_days"].mean().sort_values("_queue_days", ascending=False)

    render_chart_or_empty(
        q_df,
        chart_fn=lambda d: px.bar(
            d, x=status_col, y="_queue_days",
            title=tx("Average Queue Time by Status", "各狀態平均等待時間")
        ),
        empty_en="Not enough data to compute queue time. Missing entered date or invalid datetime format.",
        empty_zh="無法計算等待時間，可能缺少進入狀態的時間或日期格式無法解析。",
        tips=[
            tx("Required: Status_Entered_Date in ISO datetime.", "需要 Status_Entered_Date 且建議 ISO 日期格式。"),
            tx("Example: 2025-01-01 18:34:25+00:00", "例如：2025-01-01 18:34:25+00:00"),
        ],
    )

if not q_df.empty:
    top_status = str(q_df.iloc[0][status_col])
    top_days = float(q_df.iloc[0]["_queue_days"])
    note(
        f"Interpretation hint: {top_status} has the longest average waiting time {top_days:.0f} days. This is a good candidate for workflow improvement.",
        f"解讀提示：{top_status} 平均等待時間最高 {top_days:.0f} 天，通常是流程優化的優先目標。",
    )

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SECTION: SLA / Risk
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "SLA and Risk",
    "SLA 與風險",
    "Estimate potential SLA breach based on delay and priority.",
    "用延誤與優先級推估可能的 SLA 風險。",
)

sla_breach_rate = None
sla_table = pd.DataFrame()

if priority_col and delay_col and priority_col in df.columns and delay_col in df.columns:
    tmp = df[[priority_col, delay_col]].copy()
    tmp[delay_col] = pd.to_numeric(tmp[delay_col], errors="coerce")
    tmp = tmp.dropna(subset=[priority_col, delay_col])

    # simple rule: delay >= 100 considered "breach" (customizable later)
    tmp["_breach"] = tmp[delay_col] >= 100

    sla_breach_rate = tmp["_breach"].mean() * 100 if len(tmp) > 0 else None

    sla_table = (
        tmp.groupby(priority_col, as_index=False)["_breach"].mean()
        .assign(**{"Breach Rate": lambda d: d["_breach"] * 100})
        .drop(columns=["_breach"])
        .sort_values("Breach Rate", ascending=False)
    )

if sla_breach_rate is None:
    empty_state(
        "Not enough data to estimate SLA risk.",
        "資料不足以推估 SLA 風險。",
        tips=[
            tx("Need Priority and Delay columns.", "需要 Priority 與 Delay 欄位。"),
        ],
    )
else:
    st.write(f"**{tx('SLA Breach Rate', 'SLA 違規率')}：{sla_breach_rate:.1f}%**")
    st.dataframe(sla_table, use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SECTION: Root Cause Breakdown
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Root Cause Breakdown",
    "根因分類",
    "Understand what types of issues drive delays and risk.",
    "理解哪些類型的問題最常造成延誤與風險。",
)

if not (root_cause_col and root_cause_col in df.columns):
    empty_state(
        "Root cause category is missing. This section will stay empty until the column exists.",
        "缺少根因分類欄位。需要有該欄位此區塊才會顯示。",
        tips=[
            tx("Add Root_Cause column to the CSV.", "請在 CSV 加上 Root_Cause 欄位。"),
        ],
    )
else:
    rc = df[root_cause_col].dropna().astype(str)
    if rc.empty:
        empty_state(
            "Root cause column exists but has no usable values.",
            "根因欄位存在但目前沒有可用內容。",
            tips=[
                tx("Fill in at least some root cause categories.", "請填入至少部分根因分類內容。"),
            ],
        )
    else:
        rc_df = rc.value_counts().rename_axis("Root Cause").reset_index(name="Count")
        fig = px.pie(rc_df, names="Root Cause", values="Count", title=tx("Root Cause Distribution", "根因分佈"))
        st.plotly_chart(fig, use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SECTION: Blocked Details
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Blocked Details",
    "阻塞工單明細",
    "List tickets currently blocked and why they cannot move forward.",
    "列出目前被卡住的工單與卡住原因。",
)

blocked_df = pd.DataFrame()
if status_col and status_col in df.columns:
    blocked_df = df[df[status_col].astype(str).str.lower().eq("blocked")].copy()

if blocked_df.empty:
    empty_state(
        "No blocked tickets found in the current dataset.",
        "目前資料中沒有狀態為 Blocked 的工單。",
        tips=[
            tx("If you expect blocked tickets, verify Status_Current values.", "如果你預期有阻塞工單，請確認 Status_Current 的值。"),
        ],
    )
else:
    show_cols = []
    for c in [issue_key_col, summary_col, priority_col, role_col, assignee_col, blocked_reason_col]:
        if c and c in blocked_df.columns:
            show_cols.append(c)

    st.write(f"{tx('Blocked tickets', '阻塞工單數')}：{len(blocked_df)}")
    st.dataframe(blocked_df[show_cols], use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SECTION: Stale Tickets
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Stale Tickets",
    "久未更新工單",
    "Tickets not updated for a long time often indicate stalled work.",
    "長時間未更新常代表流程卡住或缺少推進。",
)

stale_df = pd.DataFrame()

if last_updated_col and last_updated_col in df.columns:
    tmp = df.copy()
    tmp[last_updated_col] = to_datetime_safe(tmp[last_updated_col])
    now_utc = pd.Timestamp.now(tz=timezone.utc)
    tmp["_stale_days"] = (now_utc - tmp[last_updated_col]).dt.total_seconds() / 86400.0

    threshold = st.slider(tx("Stale threshold days", "久未更新門檻天數"), 1, 180, 30)

    exclude_done = st.checkbox(tx("Exclude Done tickets", "排除 Done 工單"), value=True)

    stale_df = tmp.dropna(subset=["_stale_days"])
    stale_df = stale_df[stale_df["_stale_days"] >= threshold].sort_values("_stale_days", ascending=False)

    # Optional: exclude done
    if exclude_done and status_col and status_col in stale_df.columns:
        stale_df = stale_df[~stale_df[status_col].astype(str).str.lower().eq("done")]

    if stale_df.empty:
        empty_state(
            "No tickets exceed the threshold after applying filters, or timestamps are missing.",
            "套用篩選後沒有符合門檻的工單，或更新時間資料不足。",
            tips=[
                tx("Try lowering the threshold.", "可以先把門檻調小。"),
                tx("Disable exclude Done to verify data exists.", "可先取消排除 Done 來確認資料是否存在。"),
                tx("Check if Last_Updated_Date is parsable.", "確認 Last_Updated_Date 是否可解析。"),
            ],
        )
    else:
        cols = []
        for c in [issue_key_col, summary_col, priority_col, role_col, status_col, last_updated_col, "_stale_days"]:
            if c and c in stale_df.columns:
                cols.append(c)
        st.dataframe(stale_df[cols], use_container_width=True)
else:
    empty_state(
        "Not enough data to compute stale tickets. Missing Last_Updated_Date or invalid datetime format.",
        "無法計算久未更新工單。可能缺少 Last_Updated_Date 或日期格式無法解析。",
        tips=[
            tx("Add Last_Updated_Date to the export.", "請在匯出時包含 Last_Updated_Date。"),
            tx("Use ISO datetime format.", "建議使用 ISO 日期格式。"),
        ],
    )

st.markdown("</div>", unsafe_allow_html=True)

# =========================
# SECTION: Executive Summary
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Executive Summary",
    "管理摘要",
    "One-click summary for reporting.",
    "一鍵產生可匯報的摘要。",
)

if st.button(tx("Generate Executive Report", "產生匯報摘要")):
    # delay bottleneck
    delay_bottleneck = None
    if role_col and delay_col and role_col in df.columns and delay_col in df.columns:
        t = df[[role_col, delay_col]].copy()
        t[delay_col] = pd.to_numeric(t[delay_col], errors="coerce")
        t = t.dropna()
        if not t.empty:
            g = t.groupby(role_col)[delay_col].mean().sort_values(ascending=False)
            delay_bottleneck = (str(g.index[0]), float(g.iloc[0]))

    # queue bottleneck
    queue_bottleneck = None
    if status_col and status_entered_col and status_col in df.columns and status_entered_col in df.columns:
        t = df[[status_col, status_entered_col]].copy()
        t[status_entered_col] = to_datetime_safe(t[status_entered_col])
        now_utc = pd.Timestamp.now(tz=timezone.utc)
        t["_queue_days"] = (now_utc - t[status_entered_col]).dt.total_seconds() / 86400.0
        t = t.dropna(subset=[status_col, "_queue_days"])
        if not t.empty:
            g = t.groupby(status_col)["_queue_days"].mean().sort_values(ascending=False)
            queue_bottleneck = (str(g.index[0]), float(g.iloc[0]))

    # primary root cause
    primary_root_cause = None
    if root_cause_col and root_cause_col in df.columns:
        r = df[root_cause_col].dropna().astype(str)
        if not r.empty:
            primary_root_cause = r.value_counts().index[0]

    st.markdown(f"**{tx('Summary', '摘要')}**")
    bullets = []
    if delay_bottleneck:
        bullets.append(tx(
            f"Delay bottleneck: {delay_bottleneck[0]} with average delay {delay_bottleneck[1]:.1f}%",
            f"延誤熱區：{delay_bottleneck[0]} 平均延誤 {delay_bottleneck[1]:.1f}%",
        ))
    if queue_bottleneck:
        bullets.append(tx(
            f"Queue bottleneck: {queue_bottleneck[0]} with average waiting {queue_bottleneck[1]:.1f} days",
            f"等待熱區：{queue_bottleneck[0]} 平均等待 {queue_bottleneck[1]:.1f} 天",
        ))
    if sla_breach_rate is not None:
        bullets.append(tx(
            f"SLA risk: estimated breach rate {sla_breach_rate:.1f}%",
            f"SLA 風險：推估違規率 {sla_breach_rate:.1f}%",
        ))
    if primary_root_cause:
        bullets.append(tx(
            f"Primary root cause: {primary_root_cause}",
            f"主要根因：{primary_root_cause}",
        ))

    if not bullets:
        empty_state(
            "Not enough signals to generate a meaningful summary yet.",
            "目前可用訊號不足，暫時無法產出具體摘要。",
            tips=[
                tx("Add Delay, Status dates, or Root Cause columns.", "建議補充 Delay、狀態日期、根因欄位。"),
            ],
        )
    else:
        for b in bullets:
            st.write("• " + b)

st.markdown("</div>", unsafe_allow_html=True)


