import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timezone

# =========================================================
# Page config
# =========================================================
st.set_page_config(page_title="Luanta Jira Analytics", layout="wide")

# =========================================================
# Global CSS (Cards / spacing / typography)
# =========================================================
st.markdown(
    """
<style>
/* Make overall spacing calmer */
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* Card container */
.section-card {
  border: 1px solid rgba(49, 51, 63, 0.12);
  background: rgba(255,255,255,0.70);
  border-radius: 14px;
  padding: 18px 18px 10px 18px;
  margin: 14px 0 18px 0;
}

/* Card header area */
.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 0.15rem 0;
}
.section-subtitle {
  font-size: 0.92rem;
  opacity: 0.75;
  margin: 0 0 0.6rem 0;
}

/* Smaller note block */
.note {
  border-left: 4px solid rgba(0, 123, 255, 0.55);
  padding: 10px 12px;
  background: rgba(0, 123, 255, 0.06);
  border-radius: 10px;
  margin: 8px 0 10px 0;
}

/* Empty state block */
.empty {
  border-left: 4px solid rgba(255, 193, 7, 0.70);
  padding: 10px 12px;
  background: rgba(255, 193, 7, 0.10);
  border-radius: 10px;
  margin: 8px 0 10px 0;
}

/* Divider line between subparts */
.soft-divider {
  height: 1px;
  background: rgba(49, 51, 63, 0.10);
  margin: 12px 0 12px 0;
}

/* Reduce chart title noise */
h3 { margin-top: 0.5rem !important; }

/* Sidebar spacing */
section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# Language toggle
# =========================================================
LANG_OPTIONS = {
    "中文": "zh",
    "English": "en",
    "雙語": "bi",
}

st.sidebar.header("Settings")
lang_label = st.sidebar.radio("Language / 語言", list(LANG_OPTIONS.keys()), index=0)
LANG = LANG_OPTIONS[lang_label]


def tx(en: str, zh: str) -> str:
    """Return text in selected language. No parentheses. Bilingual shown as two lines."""
    if LANG == "zh":
        return zh
    if LANG == "en":
        return en
    # bilingual
    return f"{en}\n{zh}"


def card_title(en: str, zh: str, subtitle_en: str = "", subtitle_zh: str = ""):
    st.markdown(
        f"""
<div class="section-title">{tx(en, zh).replace("\n","<br/>")}</div>
<div class="section-subtitle">{tx(subtitle_en, subtitle_zh).replace("\n","<br/>")}</div>
""",
        unsafe_allow_html=True,
    )


def note(en: str, zh: str):
    st.markdown(
        f"""<div class="note">{tx(en, zh).replace("\n","<br/>")}</div>""",
        unsafe_allow_html=True,
    )


def empty_state(en: str, zh: str, tips=None):
    st.markdown(
        f"""<div class="empty">{tx(en, zh).replace("\n","<br/>")}</div>""",
        unsafe_allow_html=True,
    )
    if tips:
        with st.expander(tx("Possible reasons / Troubleshooting", "可能原因 / 排查建議"), expanded=False):
            for x in tips:
                st.write(f"- {x}")


def render_chart_or_empty(df_plot: pd.DataFrame, chart_fn, empty_en: str, empty_zh: str, tips=None):
    if df_plot is None or df_plot.empty:
        empty_state(empty_en, empty_zh, tips=tips)
        return
    fig = chart_fn(df_plot)
    st.plotly_chart(fig, use_container_width=True)


def safe_first_match(cols, keyword_list):
    """Return first column that contains any keyword (case-insensitive)."""
    for kw in keyword_list:
        for c in cols:
            if kw.lower() in c.lower():
                return c
    return None


def to_datetime_safe(s):
    return pd.to_datetime(s, errors="coerce", utc=True)


# =========================================================
# Title
# =========================================================
st.title("📊 " + tx("Luanta Service Performance Dashboard", "Luanta 服務績效儀表板"))

# =========================================================
# Sidebar - Upload
# =========================================================
st.sidebar.header(tx("Step 1: Upload Data", "步驟 1：上傳資料"))
uploaded_file = st.sidebar.file_uploader(tx("Upload Jira CSV", "上傳 Jira CSV"), type="csv")

df = None
default_loaded = None

if uploaded_file is None:
    for fn in ["Luanta_Final_Demo_Data_v1.csv", "Luanta_Final_Demo_Data.csv"]:
        try:
            df = pd.read_csv(fn)
            default_loaded = fn
            break
        except Exception:
            pass

    if df is not None:
        st.success(f"✅ {tx('Loaded default sample data', '已載入預設範例資料')}：{default_loaded}")
        note(
            "You can upload a new CSV anytime from the sidebar.",
            "你也可以隨時在左側上傳新的 CSV。",
        )
    else:
        st.warning("⚠️ " + tx("Please upload a Jira CSV to start.", "請先在左側上傳 Jira CSV 才能開始分析。"))
else:
    df = pd.read_csv(uploaded_file)
    st.success(f"✅ {tx('Successfully loaded uploaded file', '已成功讀取上傳檔案')}：{uploaded_file.name}")

if df is None:
    st.stop()

# =========================================================
# Debug / Preview
# =========================================================
with st.expander(tx("Debug info", "除錯資訊"), expanded=False):
    st.write(tx("Detected columns", "偵測到的欄位") + ":", list(df.columns))
    st.write(tx("Row count", "資料筆數") + ":", len(df))

with st.expander(tx("Data preview (first 20 rows)", "資料預覽（前 20 筆）"), expanded=False):
    st.dataframe(df.head(20), use_container_width=True)

# =========================================================
# Column detection (robust)
# =========================================================
delay_col = safe_first_match(df.columns, ["delay_rate", "delay", "delay_rate_%"])
priority_col = "Priority" if "Priority" in df.columns else safe_first_match(df.columns, ["priority"])
role_col = "Role" if "Role" in df.columns else safe_first_match(df.columns, ["role", "team"])
status_col = "Status_Current" if "Status_Current" in df.columns else safe_first_match(df.columns, ["status_current", "status"])
last_updated_col = "Last_Updated_Date" if "Last_Updated_Date" in df.columns else safe_first_match(df.columns, ["last_updated", "updated"])
status_entered_col = "Status_Entered_Date" if "Status_Entered_Date" in df.columns else safe_first_match(df.columns, ["status_entered", "entered_date"])
issue_key_col = "Issue_Key" if "Issue_Key" in df.columns else safe_first_match(df.columns, ["issue_key", "key"])
summary_col = "Summary" if "Summary" in df.columns else safe_first_match(df.columns, ["summary", "title"])
assignee_col = "Assignee" if "Assignee" in df.columns else safe_first_match(df.columns, ["assignee", "owner"])
blocked_reason_col = "Blocked_Reason" if "Blocked_Reason" in df.columns else safe_first_match(df.columns, ["blocked_reason", "block_reason", "blocked"])
root_cause_col = "Root_Cause_Category" if "Root_Cause_Category" in df.columns else safe_first_match(df.columns, ["root_cause", "cause"])

# SLA columns
sla_breached_col = "SLA_Breached" if "SLA_Breached" in df.columns else safe_first_match(df.columns, ["sla_breached", "breach"])
resolution_days_col = "Resolution_Days" if "Resolution_Days" in df.columns else safe_first_match(df.columns, ["resolution_days", "resolution_time_days", "resolution"])
sla_target_col = "SLA_Target_Days" if "SLA_Target_Days" in df.columns else safe_first_match(df.columns, ["sla_target_days", "sla_days", "sla_target"])

# =========================================================
# SECTION: Key Metrics (Card)
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Key Metrics",
    "關鍵指標",
    "High-level KPIs for a quick health check.",
    "用幾個數字快速判斷整體健康度。",
)

m1, m2, m3 = st.columns(3)
total_tickets = len(df)
m1.metric(tx("Total Tickets", "總工單數"), total_tickets)

p0_count = "N/A"
if priority_col and priority_col in df.columns:
    p0_count = int(df[priority_col].astype(str).str.contains("P0", case=False, na=False).sum())
m2.metric(tx("P0 Critical Issues", "P0 重大工單數"), p0_count)

avg_delay = "N/A"
if delay_col and delay_col in df.columns:
    avg_delay_val = pd.to_numeric(df[delay_col], errors="coerce").mean()
    if pd.notna(avg_delay_val):
        avg_delay = f"{avg_delay_val:.1f}%"
m3.metric(tx("Avg. Delay Rate", "平均延遲率"), avg_delay)

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SECTION: Performance Breakdown (Card)
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Performance Breakdown",
    "績效拆解",
    "Break down delay by role/team to locate bottlenecks.",
    "依角色拆解延遲，定位瓶頸。",
)

if not role_col or not delay_col or role_col not in df.columns or delay_col not in df.columns:
    empty_state(
        "Not enough data to show delay breakdown by role. Need Role and Delay Rate columns.",
        "目前資料不足以顯示角色延遲拆解，需要 Role 與 Delay Rate 欄位。",
        tips=[
            "確認 CSV 是否包含 Role",
            f"確認是否包含延遲欄位（例如 {delay_col or 'Delay_Rate_%'}）",
        ],
    )
else:
    perf_df = df[[role_col, delay_col]].copy()
    perf_df[delay_col] = pd.to_numeric(perf_df[delay_col], errors="coerce")
    perf_df = perf_df.dropna(subset=[role_col, delay_col])
    perf_df = perf_df.groupby(role_col, as_index=False)[delay_col].mean().sort_values(delay_col, ascending=False)

    render_chart_or_empty(
        perf_df,
        chart_fn=lambda d: px.bar(
            d,
            x=role_col,
            y=delay_col,
            color=role_col,
            labels={delay_col: "Delay Rate (%)"},
            title=tx("Average Delay by Team Role", "各角色平均延遲"),
        ),
        empty_en="Not enough numeric values to compute average delay by role.",
        empty_zh="目前資料不足以計算角色平均延遲，常見原因是延遲欄位為空或無法轉成數字。",
        tips=[
            "確認 Delay 欄位是否為數字（例如 12.3）",
            "避免混入 % 符號或文字（如 12.3%）",
        ],
    )

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SECTION: Workflow Finder (Card)
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Workflow Finder",
    "工作流程分析",
    "Use WIP and queue time to identify where the workflow is stuck.",
    "用在手量與等待時間找出流程卡點。",
)

c1, c2 = st.columns(2)

# WIP by Status
with c1:
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    st.markdown(f"### {tx('WIP by Status', '各狀態在手量')}")
    st.caption(tx("Current ticket distribution across statuses.", "工單目前分佈在哪些狀態。"))

    if not status_col or status_col not in df.columns:
        empty_state(
            "Not enough data to compute WIP by status.",
            "目前資料不足以計算各狀態在手量，常見原因是缺少 Status_Current 或欄位全空。",
            tips=[
                "確認 CSV 是否包含 Status_Current",
                "確認 Status_Current 是否有值（不是全部空白）",
            ],
        )
    else:
        wip_df = (
            df[status_col]
            .dropna()
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Count")
        )

        # ✅ 空值時顯示中性文案（不留白）
        render_chart_or_empty(
            wip_df,
            chart_fn=lambda d: px.bar(d, x="Status", y="Count", title=tx("Current Work In Progress by Status", "各狀態在手量")),
            empty_en="No usable status values found.",
            empty_zh="目前沒有可用的狀態資料可以顯示。常見原因是 Status_Current 都是空值或狀態命名不一致。",
            tips=[
                "確認 Status_Current 是否有 To Do / In Progress / Review / Done 等值",
                "如果你的狀態命名不同，建議先在 CSV 統一命名或在程式加 mapping",
            ],
        )

# Queue Time by Status
with c2:
    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
    st.markdown(f"### {tx('Queue Time (days) by Status', '各狀態等待時間（天）')}")
    st.caption(tx("Average time tickets stay in each status.", "工單在每個狀態平均停留多久，用來找最慢節點。"))

    q_df = pd.DataFrame()
    if status_col and status_entered_col and status_col in df.columns and status_entered_col in df.columns:
        tmp = df[[status_col, status_entered_col]].copy()
        tmp[status_entered_col] = to_datetime_safe(tmp[status_entered_col])
        now_utc = pd.Timestamp.now(tz=timezone.utc)
        tmp["_queue_days"] = (now_utc - tmp[status_entered_col]).dt.total_seconds() / 86400.0
        tmp = tmp.dropna(subset=[status_col, "_queue_days"])
        q_df = tmp.groupby(status_col, as_index=False)["_queue_days"].mean().sort_values("_queue_days", ascending=False)

    # ✅ 空值時顯示中性文案（不留白）
    render_chart_or_empty(
        q_df,
        chart_fn=lambda d: px.bar(d, x=status_col, y="_queue_days", title=tx("Average Queue Time by Status (days)", "各狀態平均等待時間（天）")),
        empty_en="Not enough data to compute queue time by status.",
        empty_zh="目前無法計算等待時間。常見原因是缺少 Status_Entered_Date，或日期格式無法解析。",
        tips=[
            "確認 CSV 是否包含 Status_Entered_Date",
            "日期建議使用 ISO 格式，例如 2025-01-01 18:34:25+00:00",
        ],
    )

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SECTION: Stale Tickets (Card)
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Stale Tickets",
    "久未更新工單",
    "Tickets not updated for a long time; often indicates work is stuck.",
    "長時間未更新，常代表流程卡住或缺乏推進。",
)

stale_df = pd.DataFrame()

if last_updated_col and last_updated_col in df.columns:
    tmp = df.copy()
    tmp[last_updated_col] = to_datetime_safe(tmp[last_updated_col])
    now_utc = pd.Timestamp.now(tz=timezone.utc)
    tmp["_stale_days"] = (now_utc - tmp[last_updated_col]).dt.total_seconds() / 86400.0

    threshold = st.slider(tx("Stale threshold (days)", "久未更新門檻（天）"), 1, 180, 30)

    stale_df = tmp.dropna(subset=["_stale_days"])
    stale_df = stale_df[stale_df["_stale_days"] >= threshold].sort_values("_stale_days", ascending=False)

    show_cols = []
    for c in [issue_key_col, summary_col, priority_col, role_col, status_col, last_updated_col, "_stale_days"]:
        if c and c in stale_df.columns:
            show_cols.append(c)

    if stale_df.empty:
        empty_state(
            "No tickets exceed the stale threshold, or timestamps are missing.",
            "目前沒有符合門檻的久未更新工單，或更新時間資料不足以計算。",
            tips=[
                "如果你預期會有資料，請確認 Last_Updated_Date 是否存在且為可解析日期",
                "可先把門檻天數調小看看",
            ],
        )
    else:
        st.dataframe(stale_df[show_cols], use_container_width=True)
else:
    empty_state(
        "Not enough data to compute stale tickets. Missing Last_Updated_Date or invalid datetime format.",
        "目前無法計算久未更新工單。常見原因是缺少 Last_Updated_Date 或日期格式無法解析。",
        tips=[
            "確認 CSV 是否包含 Last_Updated_Date",
            "日期建議用 ISO 格式，例如 2025-01-01 18:34:25+00:00",
        ],
    )

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SECTION: SLA / Risk (Card)
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "SLA / Risk",
    "SLA 與風險",
    "Estimate SLA breach risk if SLA columns exist.",
    "若有 SLA 欄位，估算違約風險。",
)

sla_df = pd.DataFrame()
sla_breach_rate = None
tmp = df.copy()

if sla_breached_col and sla_breached_col in tmp.columns:
    tmp[sla_breached_col] = tmp[sla_breached_col].astype(str).str.lower().isin(["true", "1", "yes", "y"])
    if priority_col and priority_col in tmp.columns:
        sla_df = tmp.groupby(priority_col, as_index=False)[sla_breached_col].mean()
        sla_df["Breach Rate (%)"] = (sla_df[sla_breached_col] * 100).round(2)
        sla_breach_rate = float(tmp[sla_breached_col].mean() * 100)

elif resolution_days_col and sla_target_col and resolution_days_col in tmp.columns and sla_target_col in tmp.columns:
    tmp[resolution_days_col] = pd.to_numeric(tmp[resolution_days_col], errors="coerce")
    tmp[sla_target_col] = pd.to_numeric(tmp[sla_target_col], errors="coerce")
    tmp["_sla_breached"] = (tmp[resolution_days_col] > tmp[sla_target_col])
    if priority_col and priority_col in tmp.columns:
        sla_df = tmp.groupby(priority_col, as_index=False)["_sla_breached"].mean()
        sla_df["Breach Rate (%)"] = (sla_df["_sla_breached"] * 100).round(2)
        sla_breach_rate = float(tmp["_sla_breached"].mean() * 100)

if sla_breach_rate is None:
    empty_state(
        "SLA fields not available. Cannot compute breach rate.",
        "缺少 SLA 欄位，無法計算違約率。",
        tips=[
            "提供 SLA_Breached（true/false）最簡單",
            "或提供 Resolution_Days + SLA_Target_Days 也可推算",
        ],
    )
else:
    st.write(f"**{tx('SLA Breach Rate', 'SLA 違約率')}**: {sla_breach_rate:.1f}%")
    if not sla_df.empty:
        show_cols = [priority_col, "Breach Rate (%)"] if (priority_col and priority_col in sla_df.columns) else ["Breach Rate (%)"]
        st.dataframe(sla_df[show_cols], use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SECTION: Root Cause Breakdown (Card)
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Root Cause Breakdown",
    "根因分佈",
    "Aggregate root causes to inform process improvements.",
    "彙整根因，指向流程改善。",
)

if not root_cause_col or root_cause_col not in df.columns:
    empty_state(
        "Missing Root_Cause_Category. Cannot show distribution.",
        "缺少 Root_Cause_Category，無法顯示根因分佈。",
        tips=["建議加入 Root_Cause_Category，例如 Spec/Requirement、API Dependency、Data/DB 等"],
    )
else:
    rc = df[root_cause_col].dropna()
    if rc.empty:
        empty_state(
            "Root cause column exists but contains no usable values.",
            "根因欄位存在，但目前沒有可用值（可能全空）。",
            tips=["確認 Root_Cause_Category 是否有填值"],
        )
    else:
        rc_df = rc.value_counts().reset_index()
        rc_df.columns = ["Root Cause", "Count"]

        render_chart_or_empty(
            rc_df,
            chart_fn=lambda d: px.pie(d, names="Root Cause", values="Count", title=tx("Root Cause Distribution", "根因分佈")),
            empty_en="Unable to render root cause distribution.",
            empty_zh="目前無法顯示根因分佈（資料可能不足）。",
        )

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SECTION: Blocked Details (Card)
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Blocked Details",
    "卡關明細",
    "Blocked tickets and reasons; good for action items.",
    "列出卡關工單與原因，方便推進。",
)

blocked_df = pd.DataFrame()
if status_col and status_col in df.columns:
    blocked_df = df[df[status_col].astype(str).str.lower().eq("blocked")].copy()

if blocked_df.empty and blocked_reason_col and blocked_reason_col in df.columns:
    blocked_df = df[df[blocked_reason_col].notna()].copy()

if blocked_df.empty:
    empty_state(
        "No blocked tickets detected.",
        "目前沒有辨識到卡關工單。",
        tips=[
            "確認 Status_Current 是否有 Blocked",
            "或提供 Blocked_Reason 欄位以利辨識",
        ],
    )
else:
    st.write(f"**{tx('Blocked tickets', '卡關工單數')}**: {len(blocked_df)}")
    cols = []
    for c in [issue_key_col, summary_col, priority_col, role_col, assignee_col, blocked_reason_col, status_col]:
        if c and c in blocked_df.columns:
            cols.append(c)
    st.dataframe(blocked_df[cols].head(50), use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SECTION: Executive Summary (Card)
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
card_title(
    "Executive Summary",
    "主管摘要",
    "Neutral, action-oriented talking points.",
    "中性且可行動的主管重點。",
)

if st.button(tx("Generate Executive Report", "產出主管摘要")):
    bullets = []

    # Delay bottleneck
    if role_col and delay_col and role_col in df.columns and delay_col in df.columns:
        tmp2 = df[[role_col, delay_col]].copy()
        tmp2[delay_col] = pd.to_numeric(tmp2[delay_col], errors="coerce")
        tmp2 = tmp2.dropna(subset=[role_col, delay_col])
        if not tmp2.empty:
            r = tmp2.groupby(role_col)[delay_col].mean().sort_values(ascending=False)
            top_role = r.index[0]
            bullets.append(tx(
                f"- Delay bottleneck: {top_role} has the highest average delay ({r.iloc[0]:.1f}%).",
                f"- 延遲瓶頸：{top_role} 平均延遲最高（{r.iloc[0]:.1f}%）。"
            ))
        else:
            bullets.append(tx(
                "- Delay bottleneck: insufficient numeric delay data.",
                "- 延遲瓶頸：延遲欄位缺乏可用數字資料。"
            ))
    else:
        bullets.append(tx(
            "- Delay bottleneck: missing Role/Delay columns.",
            "- 延遲瓶頸：缺少 Role 或 Delay 欄位。"
        ))

    # Queue bottleneck
    if status_col and status_entered_col and status_col in df.columns and status_entered_col in df.columns:
        tmp3 = df[[status_col, status_entered_col]].copy()
        tmp3[status_entered_col] = to_datetime_safe(tmp3[status_entered_col])
        now_utc = pd.Timestamp.now(tz=timezone.utc)
        tmp3["_queue_days"] = (now_utc - tmp3[status_entered_col]).dt.total_seconds() / 86400.0
        tmp3 = tmp3.dropna(subset=[status_col, "_queue_days"])
        if not tmp3.empty:
            q = tmp3.groupby(status_col)["_queue_days"].mean().sort_values(ascending=False)
            top_status = q.index[0]
            bullets.append(tx(
                f"- Queue bottleneck: {top_status} has the longest average queue time ({q.iloc[0]:.1f} days).",
                f"- 等待瓶頸：{top_status} 平均等待時間最長（{q.iloc[0]:.1f} 天）。"
            ))
        else:
            bullets.append(tx(
                "- Queue bottleneck: no usable queue-time values.",
                "- 等待瓶頸：缺乏可用等待時間資料。"
            ))
    else:
        bullets.append(tx(
            "- Queue bottleneck: missing Status_Entered_Date; cannot compute queue time.",
            "- 等待瓶頸：缺少 Status_Entered_Date，無法計算等待時間。"
        ))

    # SLA risk
    if sla_breach_rate is not None:
        bullets.append(tx(
            f"- SLA risk: breach rate is {sla_breach_rate:.1f}%.",
            f"- SLA 風險：違約率 {sla_breach_rate:.1f}%。"
        ))
    else:
        bullets.append(tx(
            "- SLA risk: SLA fields not available; not computed.",
            "- SLA 風險：缺少 SLA 欄位，未計算。"
        ))

    # Root cause
    if root_cause_col and root_cause_col in df.columns:
        rc = df[root_cause_col].dropna()
        if not rc.empty:
            top_cause = rc.value_counts().index[0]
            bullets.append(tx(
                f"- Primary root cause: {top_cause} is the most frequent category.",
                f"- 主要根因：{top_cause} 是最常見分類。"
            ))
        else:
            bullets.append(tx(
                "- Primary root cause: values are empty.",
                "- 主要根因：根因欄位目前沒有有效值。"
            ))
    else:
        bullets.append(tx(
            "- Primary root cause: missing Root_Cause_Category.",
            "- 主要根因：缺少 Root_Cause_Category。"
        ))

    st.markdown("\n".join(bullets))

st.markdown("</div>", unsafe_allow_html=True)

