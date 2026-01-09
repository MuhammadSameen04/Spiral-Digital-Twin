import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from docx import Document
from docx.shared import Inches
from io import BytesIO

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Ultra Spiral Digital Twin", layout="wide")

st.title("🌀 Ultra Digital Twin: Attock Spiral Concentrator")
st.markdown("### Process Optimization, Economics & KPI Performance Dashboard")
st.write("---")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1e2a38; color: white; }
    [data-testid="stSidebar"] .stSlider label { color: #ffcc00 !important; }
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

st.sidebar.markdown("---")
st.sidebar.subheader("🌀 Spiral Mechanics")
splitter_pos = st.sidebar.slider("Splitter Position (0=Tight, 2=Wide)", 0.0, 2.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Recovery Targets (%)")
user_targets = {m: st.sidebar.slider(f"{m} Recovery", 0.0, 100.0, float(v)) for m, v in BASE_REC.items()}

st.sidebar.header("💰 Economic Pricing ($)")
user_prices = {
    "Gold": st.sidebar.number_input("Gold ($/g)", value=80.0),
    "Magnetite": st.sidebar.number_input("Magnetite ($/t)", value=100.0),
    "Ilmenite": st.sidebar.number_input("Ilmenite ($/t)", value=250.0),
    "Rutile": st.sidebar.number_input("Rutile ($/t)", value=800.0),
    "Monazite": st.sidebar.number_input("Monazite ($/t)", value=1500.0)
}

st.sidebar.markdown("---")
st.sidebar.header("💼 Operating Cost (OPEX)")
labour_cost = st.sidebar.number_input("Labour Cost ($/hr)", value=120.0)
power_kw = st.sidebar.number_input("Installed Power (kW)", value=150.0)
power_rate = st.sidebar.number_input("Electricity Cost ($/kWh)", value=0.12)
water_cost = st.sidebar.number_input("Water Cost ($/hr)", value=15.0)
maintenance_cost = st.sidebar.number_input("Maintenance Cost ($/hr)", value=40.0)
mining_cost = st.sidebar.number_input("Mining Cost ($/ton)", value=8.0)
lease_tax = st.sidebar.number_input("Lease / Rent / Taxes ($/hr)", value=25.0)

st.sidebar.markdown("### 📈 KPI Targets")
target_margin = st.sidebar.slider("Target Profit Margin (%)", 0, 60, 25)
target_throughput = st.sidebar.slider("Target Throughput (tph)", 100, 500, 300)
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
        results.append({
            "Mineral": m, "Recovery %": round(eff_rec, 2), 
            "Conc Grade": round(grade, 4), "Revenue $/hr": round(rev, 2)
        })
    return pd.DataFrame(results), conc_mass, total_rev

def generate_heatmap_data(targets, prices, d80, solids):
    rates = np.linspace(100, 500, 10)
    splits = np.linspace(0, 2, 10)
    grid = np.zeros((10, 10))
    for i, r in enumerate(rates):
        for j, s in enumerate(splits):
            _, _, t_rev = ultra_engine(r, targets, prices, s, d80)
            t_opex = labour_cost + (power_kw * power_rate) + water_cost + maintenance_cost + (r * mining_cost) + lease_tax
            grid[i, j] = t_rev - t_opex
    return grid, rates, splits

def run_digitizer(df, splitter, rate):
    d_df = df.copy()
    d_df["Digitized Grade"] = d_df["Conc Grade"] * (1 + (splitter * 0.02))
    d_df["Digitized Recovery"] = d_df["Recovery %"] * (1 - (splitter * 0.01))
    return d_df

# --- CALCULATIONS ---
df_res, c_mass, total_revenue = ultra_engine(f_rate, user_targets, user_prices, splitter_pos, d80)
total_opex = (labour_cost + (power_kw * power_rate) + water_cost + maintenance_cost + (f_rate * mining_cost) + lease_tax)
profit_hr = total_revenue - total_opex
actual_margin = (profit_hr / total_revenue) * 100 if total_revenue > 0 else 0
cost_per_ton = total_opex / f_rate if f_rate > 0 else 0
profit_per_ton = profit_hr / f_rate if f_rate > 0 else 0

kpi_status = {
    "Throughput OK": f_rate >= target_throughput,
    "Profit Margin OK": actual_margin >= target_margin,
    "Profit/hr OK": profit_hr >= target_profit_hr
}

# Pre-calculate Heatmap for Report & Visuals
grid_data, x_labels, y_labels = generate_heatmap_data(user_targets, user_prices, d80, solids)

# --- 5. TABS & VISUALS ---
tab_viz, tab_theory, tab_export = st.tabs(["📊 Dashboard", "📖 Theory & Digitizer", "📥 Export Report"])

with tab_viz:
    c1, c2, c3 = st.columns(3)
    c1.metric("Conc Flow", f"{c_mass:.2f} tph")
    c2.metric("Total Revenue", f"${total_revenue:,.2f}/hr")
    c3.metric("Profit / hour", f"${profit_hr:,.2f}")

    k1, k2, k3 = st.columns(3)
    k1.metric("Throughput", f"{f_rate} tph")
    k2.metric("Cost / ton", f"${cost_per_ton:.2f}")
    k3.metric("Profit / ton", f"${profit_per_ton:.2f}")

    st.dataframe(df_res, use_container_width=True)

    g1, g2 = st.columns(2)
    with g1:
        fig1, ax1 = plt.subplots()
        ax1.pie(df_res["Revenue $/hr"], labels=df_res["Mineral"], autopct='%1.1f%%')
        st.pyplot(fig1)
    with g2:
        fig2, ax2 = plt.subplots()
        ax2.bar(df_res["Mineral"], df_res["Recovery %"], color='teal')
        ax2.set_ylabel("Recovery %")
        st.pyplot(fig2)

with tab_theory:
    st.header("🔬 Engineering Intelligence")
    col_ins1, col_ins2 = st.columns(2)
    with col_ins1:
        extra_money = total_revenue * 0.01
        st.metric("Profit Boost (per +1% Recovery)", f"${extra_money:,.2f}/hr")
    with col_ins2:
        breakeven_tph = total_opex / (total_revenue / f_rate) if total_revenue > 0 else 0
        st.metric("Break-even Throughput", f"{breakeven_tph:.1f} tph")

    st.write("---")
    st.subheader("🔢 Digital Twin Digitizer")
    digitized_df = run_digitizer(df_res, splitter_pos, f_rate)
    st.table(digitized_df[["Mineral", "Digitized Grade", "Digitized Recovery"]])

    st.write("---")
    st.subheader("📐 Governing Equations")
    st.latex(r"M_{feed} = M_{conc} + M_{midd} + M_{tail}")
    st.latex(r"Mass\_Pull = 10\% + (Splitter \times 10\%)")

with tab_export:
    st.subheader("📥 Export Executive Report")
    
    def make_complete_report(df, rate, total_r, split_p, grid, x_v, y_v):
        doc = Document()
        doc.add_heading('Engineering Report: Spiral Digital Twin', 0)
        doc.add_paragraph(f"Operational Summary: Feed {rate} tph, Splitter {split_p}, Revenue ${total_r:,.2f}/hr")
        
        # Add Table
        t = doc.add_table(rows=1, cols=len(df.columns))
        t.style = 'Table Grid'
        for i, col in enumerate(df.columns): t.rows[0].cells[i].text = col
        for _, row in df.iterrows():
            cells = t.add_row().cells
            for i, val in enumerate(row): cells[i].text = str(val)

        # Add Heatmap Image
        doc.add_heading('Profitability Heatmap', level=1)
        plt.figure(figsize=(8, 5))
        sns.heatmap(grid, xticklabels=np.round(y_v, 1), yticklabels=np.round(x_v, 0), cmap="RdYlGn")
        img_stream = BytesIO()
        plt.savefig(img_stream, format='png')
        doc.add_picture(img_stream, width=Inches(5))
        plt.close()

        bio = BytesIO()
        doc.save(bio)
        return bio.getvalue()

    st.download_button(
        label="📥 Download Full Executive Report (Word)",
        data=make_complete_report(df_res, f_rate, total_revenue, splitter_pos, grid_data, x_labels, y_labels),
        file_name="Spiral_Detailed_Report.docx",
        key="final_report_dl"
    )

# --- HEATMAP & KPI CHECK (BOTTOM) ---
st.write("---")
st.subheader("🔥 Profitability Heatmap (Feed Rate vs Splitter)")
fig_heat, ax_heat = plt.subplots(figsize=(10, 6))
sns.heatmap(grid_data, xticklabels=np.round(y_labels, 1), yticklabels=np.round(x_labels, 0), cmap="RdYlGn", ax=ax_heat)
st.pyplot(fig_heat)

st.markdown("### 🧠 KPI Status Check")
for k, v in kpi_status.items():
    if v: st.success(f"✅ {k}")
    else: st.error(f"❌ {k}")
