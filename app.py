import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from docx import Document
from docx.shared import Inches
from io import BytesIO
import base64

# --- MAIN PAGE HEADERS ---
st.title("🌀 Ultra Digital Twin: Attock Spiral Concentrator")
st.markdown("### Process Optimization, Economics & KPI Performance Dashboard")
st.write("---")

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Ultra Spiral Digital Twin", layout="wide")

st.markdown("""<style>
.stApp { background-color: #0e1117; color: #ffffff; }
[data-testid="stSidebar"] { background-color: #1e2a38; color: white; }
[data-testid="stSidebar"] .stSlider label { color: #ffcc00 !important; }
[data-testid="stMetricValue"] { color: #00ffcc !important; font-size: 30px; }
h1, h2, h3 { color: #ff4b4b; font-family: 'Arial'; }
</style>""", unsafe_allow_html=True)

# --- 2. BASE DATA ---
FEED_GRADES = {"Gold": 0.80, "Magnetite": 6.0, "Ilmenite": 1.5, "Rutile": 0.30, "Monazite": 0.15}
BASE_REC = {"Gold": 65.0, "Magnetite": 70.0, "Ilmenite": 60.0, "Rutile": 55.0, "Monazite": 50.0}

# --- 3. SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ Global Feed Controls")
f_rate = st.sidebar.slider("Feed Rate (tph)", 100, 500, 300)
solids = st.sidebar.slider("Solids %", 10, 50, 30)
d80 = st.sidebar.slider("Feed d80 (microns)", 20, 1000, 150)

st.sidebar.markdown("---")
st.sidebar.subheader("🌀 Spiral Mechanics")
splitter_pos = st.sidebar.slider("Splitter Position (0=Tight, 2=Wide)", 0.0, 2.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Recovery Targets (%)")
user_targets = {m: st.sidebar.slider(f"{m} Recovery", 0.0, 100.0, float(v)) for m, v in BASE_REC.items()}

st.sidebar.header("🎯 Target Grade Settings")
user_grade_targets = {m: st.sidebar.slider(f"{m} Target Grade", 0.0, 50.0, 5.0) for m in FEED_GRADES.keys()}

st.sidebar.header("💰 Economic Pricing ($)")
user_prices = {
    "Gold": st.sidebar.number_input("Gold ($/g)", value=80.0),
    "Magnetite": st.sidebar.number_input("Magnetite ($/t)", value=100.0),
    "Ilmenite": st.sidebar.number_input("Ilmenite ($/t)", value=250.0),
    "Rutile": st.sidebar.number_input("Rutile ($/t)", value=800.0),
    "Monazite": st.sidebar.number_input("Monazite ($/t)", value=1500.0)
}

# ----------- ADDITION: ECONOMICS / OPEX -----------
st.sidebar.markdown("---")
st.sidebar.header("💼 Operating Cost (OPEX)")

labour_cost = st.sidebar.number_input("Labour Cost ($/hr)", value=120.0)
power_kw = st.sidebar.number_input("Installed Power (kW)", value=150.0)
power_rate = st.sidebar.number_input("Electricity Cost ($/kWh)", value=0.12)
water_cost = st.sidebar.number_input("Water Cost ($/hr)", value=15.0)
maintenance_cost = st.sidebar.number_input("Maintenance Cost ($/hr)", value=40.0)
mining_cost = st.sidebar.number_input("Mining Cost ($/ton)", value=8.0)
lease_tax = st.sidebar.number_input("Lease / Rent / Taxes ($/hr)", value=25.0)

st.sidebar.markdown("### 📈 Margin Control")
target_margin = st.sidebar.slider("Target Profit Margin (%)", 0, 60, 25)

# ----------- KPI TARGETS (SIDEBAR ONLY) -----------
st.sidebar.markdown("---")
st.sidebar.header("📌 KPI Target Controls")

target_throughput = st.sidebar.slider(
    "Target Throughput (tph)", 100, 500, f_rate
)

target_profit_hr = st.sidebar.number_input(
    "Target Profit ($/hr)", value=5000.0
)

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
        results.append({
            "Mineral": m,
            "Recovery %": round(eff_rec, 2),
            "Conc Grade": round(grade, 4),
            "Revenue $/hr": round(rev, 2)
        })
    return pd.DataFrame(results), conc_mass, total_rev

df_res, c_mass, total_revenue = ultra_engine(f_rate, user_targets, user_prices, splitter_pos, d80)

def generate_heatmap_data(targets, prices, d80, solids):
    rates = np.linspace(100, 500, 10)
    splits = np.linspace(0, 2, 10)
    grid = np.zeros((10, 10))

    for i, r in enumerate(rates):
        for j, s in enumerate(splits):
            _, _, total_rev = ultra_engine(r, targets, prices, s, d80)
            p_cost = power_kw * power_rate
            m_cost_hr = r * mining_cost
            total_opex = labour_cost + p_cost + water_cost + maintenance_cost + m_cost_hr + lease_tax
            grid[i, j] = total_rev - total_opex
    return grid, rates, splits

power_cost = power_kw * power_rate
mining_cost_hr = f_rate * mining_cost

total_opex = labour_cost + power_cost + water_cost + maintenance_cost + mining_cost_hr + lease_tax
profit_hr = total_revenue - total_opex
actual_margin = (profit_hr / total_revenue) * 100 if total_revenue > 0 else 0

kpi_status = {
    "Throughput OK": f_rate >= target_throughput,
    "Profit Margin OK": actual_margin >= target_margin,
    "Profit/hr OK": profit_hr >= target_profit_hr
}
cost_per_ton = total_opex / f_rate
profit_per_ton = profit_hr / f_rate

