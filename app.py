
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Luanta Jira Analytics", layout="wide")
st.title("📊 Luanta Service Performance Dashboard")

st.sidebar.header("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload Jira CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # 指標計算
    total_tkt = len(df)
    p0_count = len(df[df['Priority'] == 'P0-Critical']) if 'Priority' in df.columns else 0
    avg_delay = df['Delay_Rate_%'].mean() if 'Delay_Rate_%' in df.columns else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Tickets", total_tkt)
    m2.metric("P0 Critical Issues", p0_count)
    m3.metric("Avg. Delay Rate", f"{avg_delay:.1f}%")

    st.subheader("Role-based Efficiency Analysis")
    fig = px.bar(df.groupby('Role')['Delay_Rate_%'].mean().reset_index(), 
                 x='Role', y='Delay_Rate_%', color='Role', title="Mean Delay Rate by Role")
    st.plotly_chart(fig, use_container_width=True)

    if st.button("Generate Executive Report for MG HQ"):
        st.subheader("📋 Executive Summary for Management")
        backend_rate = df[df['Role'] == 'Backend']['Delay_Rate_%'].mean()
        report = f"**Subject:** Asia Region Service Performance Gap Analysis\n\n**Key Insights:**\n- Backend Delay: {backend_rate:.1f}%\n- Bottleneck: External API dependencies."
        st.markdown(report)
