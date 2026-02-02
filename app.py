import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Luanta Jira Analytics", layout="wide")
st.title("📊 Luanta Service Performance Dashboard")

# 側邊欄上傳
st.sidebar.header("Step 1: Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload Jira CSV", type="csv")

# 如果沒上傳，我們預設讀取 GitHub 上的同名檔案（如果有）
if uploaded_file is None:
    try:
        df = pd.read_csv('Luanta_Final_Demo_Data.csv')
        st.info("💡 正在讀取預設範例數據。您也可以在上傳區丟入新檔案。")
    except:
        st.warning("請在側邊欄上傳您的 Jira CSV 檔案以開始分析。")
        df = None
else:
    df = pd.read_csv(uploaded_file)

if df is not None:
    # --- 自動偵測欄位名稱 (防呆) ---
    # 尋找包含 'Delay' 字眼的欄位，避免因為 '%' 符號報錯
    delay_col = [c for c in df.columns if 'Delay' in c][0]
    
    # 指標計算
    total_tkt = len(df)
    p0_count = len(df[df['Priority'] == 'P0-Critical']) if 'Priority' in df.columns else "N/A"
    avg_delay = df[delay_col].mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Tickets", total_tkt)
    m2.metric("P0 Critical Issues", p0_count)
    m3.metric("Avg. Delay Rate", f"{avg_delay:.1f}%")

    # 圖表區
    st.subheader("Performance Breakdown")
    fig = px.bar(df.groupby('Role')[delay_col].mean().reset_index(), 
                 x='Role', y=delay_col, color='Role', 
                 labels={delay_col: 'Delay Rate (%)'},
                 title="Average Delay by Team Role")
    st.plotly_chart(fig, use_container_width=True)

    # 向上匯報
    if st.button("Generate Executive Report"):
        st.subheader("📋 Executive Summary")
        backend_rate = df[df['Role'] == 'Backend'][delay_col].mean()
        st.markdown(f"""
        - **Core Bottleneck:** Backend team shows **{backend_rate:.1f}%** delay.
        - **Risk Level:** High (due to API integration complexity).
        - **Action Plan:** Establish clear API specifications with MG HQ to reduce back-and-forth communication.
        """)
