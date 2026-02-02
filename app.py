import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timezone

# =========================================================
# UI helpers (Bilingual + Empty state)
# =========================================================
def t(en: str, zh: str) -> str:
    return f"{en}（{zh}）"

def h1(en: str, zh: str):
    st.header(t(en, zh))

def h2(en: str, zh: str):
    st.subheader(t(en, zh))

def caption(en: str, zh: str):
    st.caption(f"{en} / {zh}")

def empty_state(
    zh: str,
    en: str = "",
    tips=None,
    level="info"
):
    msg = f"ℹ️ {en}\n\n{zh}" if en else f"ℹ️ {zh}"
    if level == "warning":
        st.warning(msg)
    else:
        st.info(msg)

    if tips:
        with st.expander(t("Possible reasons / Troubleshooting", "可能原因 / 排查建議"), expanded=False):
            for x in tips:
                st.write(f"- {x}")

def render_chart_or_empty(df_plot: pd.DataFrame, chart_fn, empty_zh: str, empty_en: str, tips=None):
    if df_plot is None or df_plot.empty:
        empty_state(empty_zh, empty_en, tips=tips, level="info")
        return
    fig = chart_fn(df_plot)
    st.plotly_chart(fig, use_container_width=True)

def safe_first_match(cols, keyword_list):
    """Return first column that contains any keyword (case-insensitive)."""
    lower_map = {c.lower(): c for c in cols}
    for kw in keyword_list:
        for c in cols:
            if kw.lower() in c.lower():
                return c
    return None

def to_datetime_safe(s):
    # Parse datetime robustly; return NaT for bad values
    return pd.to_datetime(s, errors="coerce", utc=True)

# =========================================================
# Page config
# =========================================================
st.set_page_config(page_title="Luanta Jira Analytics", layout="wide")
st.title("📊 " + t("Luanta Service Performance Dashboard", "Luanta 服務績效儀表板"))

# =========================================================
# Sidebar - Upload
# =========================================================
st.sidebar.header(t("Step 1: Upload Data", "步驟 1：上傳資料"))
uploaded_file = st.sidebar.file_uploader("Upload Jira CSV / 上傳 Jira CSV", type="csv")

# Default data fallback: v1 first, then v0
df = None
default_loaded = None

if uploaded_file is None:
    # Try v1 then v0
    for fn in ["Luanta_Final_Demo_Data_v1.csv", "Luanta_Final_Demo_Data.csv"]:
        try:
            df = pd.read_csv(fn)
            default_loaded = fn
            break
        except Exception:
            pass

    if df is not None:
        st.success(f"✅ {t('Loaded default sample data', '已載入預設範例資料')}：{default_loaded}")
        st.info("💡 " + t("You can upload a new CSV anytime from the sidebar.", "你也可以隨時在左側上傳新的 CSV。"))
    else:
        st.warning("⚠️ " + t("Please upload a Jira CSV to start.", "請先在左側上傳 Jira CSV 才能開始分析。"))
else:
    df = pd.read_csv(uploaded_file)
    st.success(f"✅ {t('Successfully loaded uploaded file', '已成功讀取上傳檔案')}：{uploaded_file.name}")

if df is None:
    st.stop()

# =========================================================
# Debug / Preview
# =========================================================
with st.expander(t("Debug info", "除錯資訊"), expanded=False):
    st.write(t("Detected columns", "偵測到的欄位") + ":", list(df.columns))
    st.write(t("Row count", "資料筆數") + ":", len(df))

with st.expander(t("Data preview (first 20 rows)", "資料預覽（前 20 筆）"), expanded=False):
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

# =========================================================
# Key Metrics
# =========================================================
h1("Key Metrics", "關鍵指標")
caption("High-level KPIs for quick health check.", "用 3 個數字快速判斷整體健康度。")

m1, m2, m3 = st.columns(3)

total_tickets = len(df)
m1.metric(t("Total Tickets", "總工單數"), total_tickets)

# P0 count
p0_count = "N/A"
if priority_col and priority_col in df.columns:
    # Common P0 labels: "P0-Critical", "P0", "Critical"
    p0_count = int(df[priority_col].astype(str).str.contains("P0", case=False, na=False).sum())
m2.metric(t("P0 Critical Issues", "P0 重大工單數"), p0_count)

avg_delay = "N/A"
if delay_col and delay_col in df.columns:
    avg_delay_val = pd.to_numeric(df[delay_col], errors="coerce").mean()
    if pd.notna(avg_delay_val):
        avg_delay = f"{avg_delay_val:.1f}%"
m3.metric(t("Avg. Delay Rate", "平均延遲率"), avg_delay)

# =========================================================
# Performance Breakdown
# =========================================================
h1("Performance Breakdown", "績效拆解")
caption("Break down delay by role/team to locate bottlenecks.", "依角色/團隊拆解延遲，定位瓶頸。")

if not role_col or not delay_col or role_col not in df.columns or delay_col not in df.columns:
    empty_state(
        zh="目前資料不足以顯示「角色延遲拆解」。需要至少包含 Role 與 Delay Rate 欄位。",
        en="Not enough data to show delay breakdown by role. Need Role and Delay Rate columns.",
        tips=[
            "確認 CSV 是否包含 Role（角色/團隊）",
            f"確認是否包含延遲欄位（例如 {delay_col or 'Delay_Rate_%'}）",
        ],
    )
else:
    perf_df = (
        df[[role_col, delay_col]]
        .copy()
    )
    perf_df[delay_col] = pd.to_numeric(perf_df[delay_col], errors="coerce")
    perf_df = perf_df.dropna(subset=[role_col, delay_col])
    perf_df = perf_df.groupby(role_col, as_index=False)[delay_col].mean().sort_values(delay_col, ascending=False)

    render_chart_or_empty(
        perf_df,
        chart_fn=lambda d: px.bar(
            d, x=role_col, y=delay_col, color=role_col,
            labels={delay_col: "Delay Rate (%)"},
            title="Average Delay by Team Role"
        ),
        empty_zh="目前資料不足以計算「角色平均延遲」。常見原因：延遲欄位為空或無法轉成數字。",
        empty_en="Not enough numeric values to compute average delay by role.",
        tips=[
            "確認 Delay 欄位是否為數字（例如 12.3）",
            "避免混入 % 符號或文字（如 '12.3%'）",
        ],
    )

# =========================================================
# Workflow Finder
# =========================================================
h1("Workflow Finder", "工作流程分析")
caption("WIP and queue time to identify where the workflow is stuck.", "用在手量與等待時間找出流程卡點。")

c1, c2 = st.columns(2)

# ---------- WIP by Status ----------
with c1:
    h2("WIP by Status", "各狀態在手量")
    caption("Shows current ticket distribution across statuses.", "顯示工單目前分佈在哪些狀態。")

    if not status_col or status_col not in df.columns:
        empty_state(
            zh="目前資料不足以計算「各狀態在手量」。常見原因：缺少 Status_Current 欄位，或欄位全為空。",
            en="Not enough data to compute WIP by status.",
            tips=[
                "確認 CSV 是否包含欄位：Status_Current",
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
        render_chart_or_empty(
            wip_df,
            chart_fn=lambda d: px.bar(d, x="Status", y="Count", title="Current Work In Progress by Status"),
            empty_zh="目前沒有可用的狀態資料可顯示（狀態可能全為空）。",
            empty_en="No usable status values found.",
            tips=["確認 Status_Current 欄位是否有填入狀態值（To Do / In Progress / Review / Done 等）"],
        )

# ---------- Queue Time by Status ----------
with c2:
    h2("Queue Time (days) by Status", "各狀態等待時間／天")
    caption("Average time tickets stay in each status (queue time).", "各狀態平均停留時間，用來找最慢節點。")

    # Compute queue days if possible
    q_df = pd.DataFrame()

    if status_col and status_entered_col and status_col in df.columns and status_entered_col in df.columns:
        tmp = df[[status_col, status_entered_col]].copy()
        tmp[status_entered_col] = to_datetime_safe(tmp[status_entered_col])

        # Use "now" in UTC for consistent calc (demo data might be old; still OK for illustration)
        now_utc = pd.Timestamp.now(tz=timezone.utc)
        tmp["_queue_days"] = (now_utc - tmp[status_entered_col]).dt.total_seconds() / 86400.0
        tmp = tmp.dropna(subset=[status_col, "_queue_days"])

        q_df = tmp.groupby(status_col, as_index=False)["_queue_days"].mean().sort_values("_queue_days", ascending=False)

    render_chart_or_empty(
        q_df,
        chart_fn=lambda d: px.bar(d, x=status_col, y="_queue_days", title="Average Queue Time by Status (days)"),
        empty_zh="目前資料不足以計算「等待時間（Queue Time）」。常見原因：缺少狀態進入時間（例如 Status_Entered_Date），或日期格式無法解析。",
        empty_en="Not enough data to compute queue time by status.",
        tips=[
            "確認 CSV 是否包含：Status_Entered_Date（進入目前狀態的時間）",
            "日期格式建議用 ISO（例如 2025-01-01 18:34:25+00:00）",
        ],
    )

# =========================================================
# Stale Tickets
# =========================================================
h1("Stale Tickets (no update)", "久未更新工單")
caption("Tickets that haven't been updated for a long time; often indicates workflow stuck.", "長時間未更新，常代表流程卡住或缺乏推進。")

stale_df = pd.DataFrame()

if last_updated_col and last_updated_col in df.columns:
    tmp = df.copy()
    tmp[last_updated_col] = to_datetime_safe(tmp[last_updated_col])
    now_utc = pd.Timestamp.now(tz=timezone.utc)
    tmp["_stale_days"] = (now_utc - tmp[last_updated_col]).dt.total_seconds() / 86400.0

    # Default threshold: 14 days
    threshold = st.slider(t("Stale threshold (days)", "久未更新門檻（天）"), 1, 180, 30)

    stale_df = tmp.dropna(subset=["_stale_days"])
    stale_df = stale_df[stale_df["_stale_days"] >= threshold].sort_values("_stale_days", ascending=False)

    show_cols = []
    for c in [issue_key_col, summary_col, priority_col, role_col, status_col, last_updated_col, "_stale_days"]:
        if c and c in stale_df.columns:
            show_cols.append(c)

    if stale_df.empty:
        empty_state(
            zh="目前沒有符合「久未更新」門檻的工單，或資料中的更新時間不足以計算。",
            en="No tickets exceed the stale threshold, or timestamps are missing.",
            tips=["如果你期待看到資料，請確認 Last_Updated_Date 是否存在且可解析為日期。"],
        )
    else:
        st.dataframe(stale_df[show_cols], use_container_width=True)

else:
    empty_state(
        zh="目前資料不足以計算「久未更新工單」。常見原因：缺少 Last_Updated_Date 欄位，或日期格式無法解析。",
        en="Not enough data to compute stale tickets. Missing Last_Updated_Date or invalid datetime format.",
        tips=[
            "確認 CSV 是否包含：Last_Updated_Date",
            "日期格式建議用 ISO（例如 2025-01-01 18:34:25+00:00）",
        ],
    )

# =========================================================
# SLA / Risk
# =========================================================
h1("SLA / Risk", "SLA 與風險")
caption("Estimate SLA breach risk; depends on whether SLA columns exist.", "估算 SLA 違約風險；需要有 SLA 相關欄位。")

sla_df = pd.DataFrame()
sla_breach_rate = None

# Option A: SLA_Breached exists
sla_breached_col = "SLA_Breached" if "SLA_Breached" in df.columns else safe_first_match(df.columns, ["sla_breached", "breach"])

# Option B: Resolution_Days + SLA_Target_Days exist
resolution_days_col = "Resolution_Days" if "Resolution_Days" in df.columns else safe_first_match(df.columns, ["resolution_days", "resolution_time_days", "resolution"])
sla_target_col = "SLA_Target_Days" if "SLA_Target_Days" in df.columns else safe_first_match(df.columns, ["sla_target_days", "sla_days", "sla_target"])

tmp = df.copy()

if sla_breached_col and sla_breached_col in tmp.columns:
    # Normalize boolean-ish values
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
        zh="目前資料不足以計算 SLA 違約率。常見原因：缺少 SLA_Breached，或缺少 Resolution_Days + SLA_Target_Days。",
        en="Not enough data to compute SLA breach rate. Missing SLA_Breached or (Resolution_Days + SLA_Target_Days).",
        tips=[
            "如果你希望計算 SLA，建議在 CSV 加入 SLA_Target_Days 與 Resolution_Days（或直接提供 SLA_Breached）。",
        ],
    )
else:
    st.write(f"**{t('SLA Breach Rate', 'SLA 違約率')}**: {sla_breach_rate:.1f}%")
    if not sla_df.empty:
        show_cols = [priority_col, "Breach Rate (%)"] if (priority_col and priority_col in sla_df.columns) else ["Breach Rate (%)"]
        st.dataframe(sla_df[show_cols], use_container_width=True)

# =========================================================
# Root Cause Breakdown
# =========================================================
h1("Root Cause Breakdown", "根因分佈")
caption("Aggregate probable root causes to inform process improvements.", "彙整根因，指向流程改善與制度化。")

if not root_cause_col or root_cause_col not in df.columns:
    empty_state(
        zh="目前資料不足以顯示根因分佈。常見原因：缺少 Root_Cause_Category 欄位。",
        en="Not enough data to show root cause distribution. Missing Root_Cause_Category.",
        tips=[
            "建議在 CSV 加入 Root_Cause_Category（例如 Spec/Requirement、API Dependency、Data/DB 等）",
        ],
    )
else:
    rc = df[root_cause_col].dropna()
    if rc.empty:
        empty_state(
            zh="根因欄位存在，但目前沒有可用值（可能全為空）。",
            en="Root cause column exists but contains no usable values.",
            tips=["確認 Root_Cause_Category 是否有填值。"],
        )
    else:
        rc_df = rc.value_counts().reset_index()
        rc_df.columns = ["Root Cause", "Count"]
        rc_df["Share (%)"] = (rc_df["Count"] / rc_df["Count"].sum() * 100).round(1)

        render_chart_or_empty(
            rc_df,
            chart_fn=lambda d: px.pie(d, names="Root Cause", values="Count", title="Root Cause Distribution"),
            empty_zh="目前無法顯示根因分佈（資料可能不足）。",
            empty_en="Unable to render root cause distribution.",
        )

# =========================================================
# Blocked Details
# =========================================================
h1("Blocked Details", "卡關明細")
caption("Tickets currently blocked and the reasons; good for action items.", "列出目前卡關工單與原因，方便開會推進。")

blocked_df = pd.DataFrame()
if status_col and status_col in df.columns:
    blocked_df = df[df[status_col].astype(str).str.lower().eq("blocked")].copy()

# If no explicit status=Blocked, fallback: blocked reason exists
if blocked_df.empty and blocked_reason_col and blocked_reason_col in df.columns:
    blocked_df = df[df[blocked_reason_col].notna()].copy()

if blocked_df.empty:
    empty_state(
        zh="目前沒有可辨識的卡關工單（Blocked）。若你預期有資料，可能是狀態命名不同或缺少 Blocked_Reason。",
        en="No blocked tickets detected. Status naming may differ or Blocked_Reason is missing.",
        tips=[
            "確認 Status_Current 是否包含 'Blocked' 狀態",
            "或在 CSV 提供 Blocked_Reason 欄位以利辨識",
        ],
    )
else:
    st.write(f"**{t('Blocked tickets', '卡關工單數')}**: {len(blocked_df)}")

    cols = []
    for c in [issue_key_col, summary_col, priority_col, role_col, assignee_col, blocked_reason_col, status_col]:
        if c and c in blocked_df.columns:
            cols.append(c)

    st.dataframe(blocked_df[cols].head(50), use_container_width=True)

# =========================================================
# Executive Summary
# =========================================================
h1("Executive Summary", "主管摘要")
caption("Auto-generated talking points for managers; neutral and action-oriented.", "自動生成主管可用的重點摘要：中性、可行動。")

if st.button(t("Generate Executive Report", "產出主管摘要")):
    bullets = []

    # Delay bottleneck
    if role_col and delay_col and role_col in df.columns and delay_col in df.columns:
        tmp = df[[role_col, delay_col]].copy()
        tmp[delay_col] = pd.to_numeric(tmp[delay_col], errors="coerce")
        tmp = tmp.dropna(subset=[role_col, delay_col])
        if not tmp.empty:
            r = tmp.groupby(role_col)[delay_col].mean().sort_values(ascending=False)
            top_role = r.index[0]
            bullets.append(f"- **{t('Delay Bottleneck', '延遲瓶頸')}**: {top_role} {t('has the highest average delay', '平均延遲最高')} ({r.iloc[0]:.1f}%).")
        else:
            bullets.append(f"- **{t('Delay Bottleneck', '延遲瓶頸')}**: {t('Insufficient numeric delay data', '延遲欄位無有效數字資料')}。")
    else:
        bullets.append(f"- **{t('Delay Bottleneck', '延遲瓶頸')}**: {t('Missing Role/Delay columns', '缺少 Role 或 Delay 欄位')}。")

    # Queue bottleneck
    if status_col and status_entered_col and status_col in df.columns and status_entered_col in df.columns:
        tmp = df[[status_col, status_entered_col]].copy()
        tmp[status_entered_col] = to_datetime_safe(tmp[status_entered_col])
        now_utc = pd.Timestamp.now(tz=timezone.utc)
        tmp["_queue_days"] = (now_utc - tmp[status_entered_col]).dt.total_seconds() / 86400.0
        tmp = tmp.dropna(subset=[status_col, "_queue_days"])
        if not tmp.empty:
            q = tmp.groupby(status_col)["_queue_days"].mean().sort_values(ascending=False)
            top_status = q.index[0]
            bullets.append(f"- **{t('Queue Bottleneck', '流程等待瓶頸')}**: {top_status} {t('has the longest average queue time', '平均等待時間最長')} ({q.iloc[0]:.1f} {t('days', '天')}).")
        else:
            bullets.append(f"- **{t('Queue Bottleneck', '流程等待瓶頸')}**: {t('No usable queue-time values', '無可用等待時間數值')}。")
    else:
        bullets.append(f"- **{t('Queue Bottleneck', '流程等待瓶頸')}**: {t('Missing Status_Entered_Date (queue-time) field', '缺少 Status_Entered_Date 無法計算等待時間')}。")

    # SLA risk
    if sla_breach_rate is not None:
        bullets.append(f"- **{t('SLA Risk', 'SLA 風險')}**: {t('Breach rate is', '違約率為')} {sla_breach_rate:.1f}%.")
    else:
        bullets.append(f"- **{t('SLA Risk', 'SLA 風險')}**: {t('SLA fields not available; risk not computed', '缺少 SLA 欄位，未計算風險')}。")

    # Root cause
    if root_cause_col and root_cause_col in df.columns:
        rc = df[root_cause_col].dropna()
        if not rc.empty:
            top_cause = rc.value_counts().index[0]
            bullets.append(f"- **{t('Primary Root Cause', '主要根因')}**: {top_cause} {t('is the most frequent category', '為最常見分類')}。")
        else:
            bullets.append(f"- **{t('Primary Root Cause', '主要根因')}**: {t('Root-cause values are empty', '根因欄位目前無有效值')}。")
    else:
        bullets.append(f"- **{t('Primary Root Cause', '主要根因')}**: {t('Missing Root_Cause_Category', '缺少 Root_Cause_Category 欄位')}。")

    st.markdown("\n".join(bullets))
    st.caption(t("Tip: Use these bullets in a weekly review or exec update.", "提示：可直接貼到週報/主管更新/跨部門會議紀錄。"))
