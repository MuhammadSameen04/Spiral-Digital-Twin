import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from docx import Document
from docx.shared import Inches
from io import BytesIO

# 1. SETTINGS (MUST BE FIRST)
st.set_page_config(page_title="Ultra Spiral Digital Twin", layout="wide")

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1e2a38; color: white; }
    [data-testid="stMetricValue"] { color: #00ffcc !important; font-size: 30px; }
    h1, h2, h3 { color: #ff4b4b; font-family: 'Arial'; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DATA ---
FEED_GRADES = {"Gold": 0.80, "Magnetite": 6.0, "Ilmenite": 1.5, "Rutile": 0.30, "Monazite": 0.15}
BASE_REC = {"Gold": 65.0, "Magnetite": 70.0, "Ilmenite": 60.0, "Rutile": 55.0, "Monazite": 50.0}

# --- 3. SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ Global Feed Controls")
f_rate = st.sidebar.slider("Feed Rate (tph)", 100, 500, 300)
solids = st.sidebar.slider("Solids %", 10, 50, 30)
d80 = st.sidebar.slider("Feed d80 (microns)", 20, 1000, 150)
splitter_pos = st.sidebar.slider("Splitter Position (0=Tight, 2=Wide)", 0.0, 2.0, 1.0)

st.sidebar.header("💰 Economic Pricing ($)")
user_prices = {
    "Gold": st.sidebar.number_input("Gold ($/g)", value=80.0),
    "Magnetite": st.sidebar.number_input("Magnetite ($/t)", value=100.0),
    "Ilmenite": st.sidebar.number_input("Ilmenite ($/t)", value=250.0),
    "Rutile": st.sidebar.number_input("Rutile ($/t)", value=800.0),
    "Monazite": st.sidebar.number_input("Monazite ($/t)", value=1500.0)
}

st.sidebar.header("💼 Operating Cost (OPEX)")
labour_cost = st.sidebar.number_input("Labour Cost ($/hr)", value=120.0)
power_kw = st.sidebar.number_input("Installed Power (kW)", value=150.0)
power_rate = st.sidebar.number_input("Electricity Cost ($/kWh)", value=0.12)
water_cost = st.sidebar.number_input("Water Cost ($/hr)", value=15.0)
maintenance_cost = st.sidebar.number_input("Maintenance Cost ($/hr)", value=40.0)
mining_cost = st.sidebar.number_input("Mining Cost ($/ton)", value=8.0)
lease_tax = st.sidebar.number_input("Lease Taxes ($/hr)", value=25.0)

st.sidebar.header("📌 KPI Targets")
target_throughput = st.sidebar.slider("Target Throughput (tph)", 100, 500, 300)
target_profit_margin = st.sidebar.slider("Target Profit Margin (%)", 0, 60, 25)
target_profit_hr = st.sidebar.number_input("Target Profit ($/hr)", value=5000.0)

# --- 4. ENGINE LOGIC ---
def ultra_engine(rate, targets, prices, split_pos, size_d80):
    size_factor = 1.0
    if size_d80 < 100: size_factor = size_d80 / 100
    elif size_d80 > 400: size_factor = max(0.4, 1.0 - (size_d80 - 400) / 800)
    mass_pull = 0.10 + (split_pos * 0.10)
    conc_mass = rate * mass_pull
    results = []
    total_rev = 0
    for m, rec in targets.items():
        eff_rec = rec * size_factor
        feed_m = rate * (FEED_GRADES[m] if m == "Gold" else FEED_GRADES[m]/100)
        conc_m = feed_m * (eff_rec/100)
        grade = conc_m / conc_mass if m == "Gold" else (conc_m/conc_mass)*100
        rev = conc_m * prices[m]
        total_rev += rev
        results.append({"Mineral": m, "Recovery %": round(eff_rec, 2), "Conc Grade": round(grade, 4), "Revenue $/hr": round(rev, 2)})
    return pd.DataFrame(results), conc_mass, total_rev

def generate_heatmap_data(targets, prices, d80):
    rates = np.linspace(100, 500, 10)
    splits = np.linspace(0, 2, 10)
    grid = np.zeros((10, 10))
    for i, r in enumerate(rates):
        for j, s in enumerate(splits):
            _, _, total_rev = ultra_engine(r, targets, prices, s, d80)
            total_opex = labour_cost + (power_kw * power_rate) + water_cost + maintenance_cost + (r * mining_cost) + lease_tax
            grid[i, j] = total_rev - total_opex
    return grid, rates, splits

# --- CALCULATIONS ---
df_res, c_mass, total_revenue = ultra_engine(f_rate, BASE_REC, user_prices, splitter_pos, d80)
total_opex = labour_cost + (power_kw * power_rate) + water_cost + maintenance_cost + (f_rate * mining_cost) + lease_tax
profit_hr = total_revenue - total_opex
actual_margin = (profit_hr / total_revenue) * 100 if total_revenue > 0 else 0
cost_per_ton = total_opex / f_rate if f_rate > 0 else 0

# --- UI DISPLAY ---
st.title("🌀 Ultra Digital Twin: Attock Spiral")
tab_viz, tab_theory, tab_export = st.tabs(["📊 Dashboard", "📖 Theory", "📥 Export"])

with tab_viz:
    m1, m2, m3 = st.columns(3)
    m1.metric("Revenue", f"${total_revenue:,.2f}/hr")
    m2.metric("Profit", f"${profit_hr:,.2f}/hr")
    m3.metric("Margin", f"{actual_margin:.1f}%")

    st.dataframe(df_res, use_container_width=True)

    st.subheader("🔥 Profitability Heatmap")
    grid_data, x_labels, y_labels = generate_heatmap_data(BASE_REC, user_prices, d80)
    fig_heat, ax_heat = plt.subplots(figsize=(8, 4))
    sns.heatmap(grid_data, xticklabels=np.round(y_labels, 1), yticklabels=np.round(x_labels, 0), cmap="RdYlGn", ax=ax_heat)
    st.pyplot(fig_heat)

    st.subheader("🧠 KPI Status")
    kpi_status = {"Throughput OK": f_rate >= target_throughput, "Margin OK": actual_margin >= target_profit_margin, "Profit OK": profit_hr >= target_profit_hr}
    for k, v in kpi_status.items():
        if v: st.success(f"✅ {k}")
        else: st.error(f"❌ {k}")

with tab_export:
    def make_report(df, rate, total_r, profit):
        doc = Document()
        doc.add_heading('Engineering Report: Spiral Digital Twin', 0)
        doc.add_paragraph(f"Throughput: {rate} tph | Revenue: ${total_r:,.2f} | Profit: ${profit:,.2f}")
        bio = BytesIO(); doc.save(bio)
        return bio.getvalue()

    st.download_button(
        label="📥 Download Report",
        data=make_report(df_res, f_rate, total_revenue, profit_hr),
        file_name="Spiral_Report.docx",
        key="report_btn"
    )
