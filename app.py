import pandas as pd
import numpy as np
from pathlib import Path

df = pd.read_csv("/mnt/data/Luanta_Final_Demo_Data.csv").copy()

colmap = {
    "Created_Date (日期)": "Created_Date",
    "Issue_Key (卡片編號)": "Issue_Key",
    "Summary (任務內容)": "Summary",
    "Delay_Rate_%": "Delay_Rate",
}
df = df.rename(columns=colmap)
df["Created_Date"] = pd.to_datetime(df["Created_Date"], errors="coerce")

rng = np.random.default_rng(42)

sla_map = {"P0-Critical": 24, "P1-High": 72, "P2-Medium": 120, "P3-Low": 240}
df["SLA_Hours"] = df["Priority"].map(sla_map).fillna(120).astype(int)

actual = pd.to_numeric(df.get("Actual_Hrs", pd.Series([np.nan]*len(df))), errors="coerce").fillna(8).clip(lower=0.5)
elapsed_hours = (actual * rng.uniform(1.2, 2.2, size=len(df))).round(1)

in_progress_mask = rng.random(len(df)) < 0.22
df["Resolved_Date"] = df["Created_Date"] + pd.to_timedelta(elapsed_hours, unit="h")
df.loc[in_progress_mask, "Resolved_Date"] = pd.NaT

last_update_hours = elapsed_hours * rng.uniform(0.6, 1.0, size=len(df))
df["Last_Updated_Date"] = df["Created_Date"] + pd.to_timedelta(last_update_hours, unit="h")
df["Last_Updated_Date"] = df[["Last_Updated_Date", "Resolved_Date"]].min(axis=1)

delay = pd.to_numeric(df.get("Delay_Rate", pd.Series([0]*len(df))), errors="coerce").fillna(0)
reopen = pd.to_numeric(df.get("Re_open_Count", pd.Series([0]*len(df))), errors="coerce").fillna(0)

status = []
for i in range(len(df)):
    if pd.notna(df.loc[i, "Resolved_Date"]):
        if reopen.iloc[i] >= 2:
            status.append("Done")
        elif delay.iloc[i] >= 80:
            status.append(rng.choice(["Done", "QA"], p=[0.7, 0.3]))
        else:
            status.append("Done")
    else:
        if delay.iloc[i] >= 90:
            status.append(rng.choice(["Blocked", "Review"], p=[0.6, 0.4]))
        elif reopen.iloc[i] >= 2:
            status.append(rng.choice(["QA", "Review"], p=[0.6, 0.4]))
        else:
            status.append(rng.choice(["In Progress", "To Do", "Review"], p=[0.6, 0.2, 0.2]))
df["Status_Current"] = status

status_entered_ratio = rng.uniform(0.2, 0.9, size=len(df))
df["Status_Entered_Date"] = df["Created_Date"] + (df["Last_Updated_Date"] - df["Created_Date"]) * status_entered_ratio

assignees_by_role = {
    "Backend": ["Alex", "Ben", "Cindy", "Derek"],
    "Frontend": ["Ethan", "Fiona", "Grace"],
    "QA": ["Helen", "Ian"],
    "PM": ["Rosa", "Jamie"],
    "DevOps": ["Kai", "Leo"],
    "Data": ["Mia", "Nina"],
}
def pick_assignee(role):
    pool = assignees_by_role.get(str(role), ["Sam", "Taylor"])
    return rng.choice(pool)

df["Assignee"] = df["Role"].apply(pick_assignee)

summary_lower = df["Summary"].astype(str).str.lower()

root = np.select(
    [
        summary_lower.str.contains(r"api|endpoint|callback|integration"),
        summary_lower.str.contains(r"payment|gateway|transaction"),
        summary_lower.str.contains(r"slot|game"),
        summary_lower.str.contains(r"db|database|query"),
    ],
    [
        "API Dependency",
        "Payments / PSP",
        "Game Feature / Content",
        "Data / DB",
    ],
    default="Spec / Requirement",
)
df["Root_Cause_Category"] = root

blocked_reasons = [
    "Waiting for HQ API clarification",
    "Waiting for vendor/PSP response",
    "Dependency on upstream service release",
    "Pending security review",
    "Awaiting UAT sign-off",
]
df["Blocked_Reason"] = np.where(df["Status_Current"].eq("Blocked"), rng.choice(blocked_reasons, size=len(df)), "")

upstream_choices = ["MG HQ", "PSP Vendor", "Internal Platform", "Compliance", "N/A"]
downstream_choices = ["Client Ops", "Finance", "CS", "N/A"]
df["Upstream_Team"] = rng.choice(upstream_choices, size=len(df))
df["Downstream_Team"] = rng.choice(downstream_choices, size=len(df))

df["Handoff_Count"] = (rng.integers(0, 2, size=len(df)) + (reopen > 0).astype(int) + (delay >= 80).astype(int)).clip(0, 5)

df["Lead_Time_Hours"] = (df["Resolved_Date"] - df["Created_Date"]).dt.total_seconds() / 3600
df["SLA_Breached"] = np.where(df["Resolved_Date"].notna() & (df["Lead_Time_Hours"] > df["SLA_Hours"]), "Y", "N")

ordered = [
    "Issue_Key", "Summary", "Role", "Assignee", "Priority",
    "Created_Date", "Last_Updated_Date", "Status_Current", "Status_Entered_Date", "Resolved_Date",
    "Estimate_Hrs", "Actual_Hrs", "Delay_Rate", "Re_open_Count",
    "Handoff_Count", "SLA_Hours", "SLA_Breached", "Lead_Time_Hours",
    "Root_Cause_Category", "Blocked_Reason", "Upstream_Team", "Downstream_Team"
]
for c in df.columns:
    if c not in ordered:
        ordered.append(c)

df_out = df[ordered].copy()

out_path = Path("/mnt/data/Luanta_Final_Demo_Data_v1.csv")
df_out.to_csv(out_path, index=False, encoding="utf-8-sig")

(out_path.as_posix(), df_out.head(3))
