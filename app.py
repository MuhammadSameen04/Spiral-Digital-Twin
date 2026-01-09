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
            "Mineral": m,
            "Recovery %": round(eff_rec, 2),
            "Conc Grade": round(grade, 4),
            "Revenue $/hr": round(rev, 2)
        })
    return pd.DataFrame(results), conc_mass, total_rev

# --- CALCULATIONS (ORDER FIXED HERE) ---

# 1. Run Engine first to get revenue
df_res, c_mass, total_revenue = ultra_engine(f_rate, user_targets, user_prices, splitter_pos, d80)

# 2. Calculate OPEX
power_cost = power_kw * power_rate
mining_cost_hr = f_rate * mining_cost
total_opex = (labour_cost + power_cost + water_cost + maintenance_cost + mining_cost_hr + lease_tax)

# 3. Calculate Profit and Margin (Now variables are defined)
profit_hr = total_revenue - total_opex
actual_margin = (profit_hr / total_revenue) * 100 if total_revenue > 0 else 0

# 4. KPI Status check using correct variable names
kpi_status = {
    "Throughput OK": f_rate >= target_throughput,
    "Profit Margin OK": actual_margin >= target_margin,
    "Profit/hr OK": profit_hr >= target_profit_hr
}

cost_per_ton = total_opex / f_rate if f_rate > 0 else 0
profit_per_ton = profit_hr / f_rate if f_rate > 0 else 0

# Heatmap function
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
    
# --- ADVANCED DIGITIZER LOGIC ---
def run_digitizer(df, splitter, rate):
    d_df = df.copy()
    # Logic: Splitter movement affects Grade and Recovery inversely
    d_df["Digitized Grade"] = d_df["Conc Grade"] * (1 + (splitter * 0.02))
    d_df["Digitized Recovery"] = d_df["Recovery %"] * (1 - (splitter * 0.01))
    d_df["Digitized TPH"] = (rate * (d_df["Digitized Recovery"]/100)) * (FEED_GRADES["Gold"]/100) # Simplified
    return d_df

# --- SENSITIVITY INSIGHTS ---
def get_expert_insights(total_rev, current_rec_avg):
    # 1% Recovery Increase Calculation
    extra_profit_per_1pct = total_rev * 0.01
    return extra_profit_per_1pct
    
    # --- EXPERT INSIGHTS SECTION ---
    st.subheader("💡 Expert Insights (Financial Sensitivity)")
    extra_money = get_expert_insights(total_revenue, df_res["Recovery %"].mean())
    
    col_ins1, col_ins2 = st.columns(2)
    with col_ins1:
        st.metric("Profit Boost (per +1% Recovery)", f"${extra_money:,.2f}/hr")
        st.write(f"Agar aap plant ki overall recovery **1%** barha lete hain, toh aapka munafa mahana **${extra_money*24*30:,.0f}** barh sakta hai.")
    
    with col_ins2:
        breakeven_tph = total_opex / (total_revenue / f_rate) if total_revenue > 0 else 0
        st.metric("Break-even Throughput", f"{breakeven_tph:.1f} tph")
        st.write(f"Aapko kam az kam **{breakeven_tph:.1f} tph** feed rate chahiye taaki aapka OPEX cover ho sake.")

    # --- DIGITIZER SECTION ---
    st.write("---")
    st.subheader("🔢 Digital Twin Digitizer (Grade-Recovery-TPH)")
    st.caption("Adjusted values based on current Splitter Position and Feed Rate")
    
    digitized_results = run_digitizer(df_res, splitter_pos, f_rate)
    
    # Display Digitized Table
    st.table(digitized_results[["Mineral", "Digitized Grade", "Digitized Recovery", "Revenue $/hr"]])

    # --- EQUATIONS ---
    st.write("---")
    st.subheader("📐 Governing Equations")
    st.latex(r"M_{conc} = M_{feed} \times (0.10 + 0.10 \times \text{Splitter})")
    st.latex(r"Revenue\ Sensitivity = \sum (Grade_i \times Price_i) \times 0.01")

# --- 5. TABS & VISUALS ---
tab_viz, tab_theory, tab_export = st.tabs(["📊 Dashboard", "📖 Theory & Equations", "📥 Export Report"])

with tab_viz:
    c1, c2, c3 = st.columns(3)
    c1.metric("Conc Flow", f"{c_mass:.2f} tph")
    c2.metric("Total Revenue", f"${total_revenue:,.2f}/hr")
    c3.metric("Feed Size", f"{d80} µm")

    k1, k2, k3 = st.columns(3)
    k1.metric("Throughput", f"{f_rate} tph")
    k2.metric("Cost / ton", f"${cost_per_ton:.2f}")
    k3.metric("Profit / hour", f"${profit_hr:,.2f}")

    k4, k5 = st.columns(2)
    k4.metric("Profit / ton", f"${profit_per_ton:.2f}")
    k5.metric("Total OPEX", f"${total_opex:,.2f}/hr")

    st.dataframe(df_res, use_container_width=True)

    g1, g2 = st.columns(2)
    with g1:
        fig1, ax1 = plt.subplots()
        ax1.pie(df_res["Revenue $/hr"], labels=df_res["Mineral"], autopct='%1.1f%%')
        st.pyplot(fig1)

    with g2:
        fig2, ax2 = plt.subplots()
        ax2.bar(df_res["Mineral"], df_res["Recovery %"])
        ax2.set_ylabel("Recovery %")
        st.pyplot(fig2)

with tab_theory:
    st.subheader("📚 Engineering Logic")
    st.latex(r"M_{feed} = M_{conc} + M_{midd} + M_{tail}")
    st.latex(r"Mass\_Pull = 10\% + (Splitter\_Position \times 10\%)")

with tab_export:
    st.subheader("📥 Export Executive Report")
    st.info("Generating this report will include the Mineral Table, Bar Charts, and the Profitability Heatmap.")

    def make_complete_report(df, rate, conc_m, d80_v, total_r, split_p, grid, x_vals, y_vals):
        doc = Document()
        doc.add_heading('Engineering Report: Spiral Digital Twin', 0)
        
        # 1. Summary Section
        doc.add_heading('1. Operational Summary', level=1)
        doc.add_paragraph(f"Feed Rate: {rate} tph")
        doc.add_paragraph(f"Feed d80: {d80_v} µm")
        doc.add_paragraph(f"Splitter Position: {split_p}")
        doc.add_paragraph(f"Total Revenue: ${total_r:,.2f}/hr")

        # 2. Mineral Data Table
        doc.add_heading('2. Mineral Recovery & Grade Data', level=1)
        table = doc.add_table(rows=1, cols=len(df.columns))
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        for i, col in enumerate(df.columns):
            hdr_cells[i].text = col
        for _, row in df.iterrows():
            row_cells = table.add_row().cells
            for i, val in enumerate(row):
                row_cells[i].text = str(val)

        # 3. Bar Chart & Visuals
        doc.add_heading('3. Performance Visuals', level=1)
        
        # Saving Bar Chart to Buffer
        fig_bar, ax_bar = plt.subplots(figsize=(6, 4))
        ax_bar.bar(df["Mineral"], df["Recovery %"], color='teal')
        ax_bar.set_title("Recovery % by Mineral")
        buf_bar = BytesIO()
        plt.savefig(buf_bar, format='png')
        buf_bar.seek(0)
        doc.add_picture(buf_bar, width=Inches(5))
        plt.close(fig_bar)

        # 4. Profitability Heatmap
        doc.add_heading('4. Economic Heatmap (Profitability)', level=1)
        fig_h, ax_h = plt.subplots(figsize=(8, 5))
        sns.heatmap(grid, xticklabels=np.round(y_vals, 1), yticklabels=np.round(x_vals, 0), cmap="RdYlGn", ax=ax_h)
        ax_h.set_title("Feed Rate vs Splitter Profitability")
        buf_heat = BytesIO()
        plt.savefig(buf_heat, format='png')
        buf_heat.seek(0)
        doc.add_picture(buf_heat, width=Inches(5))
        plt.close(fig_h)

        # Save Final Document
        bio = BytesIO()
        doc.save(bio)
        return bio.getvalue()

    # Download Button
    report_data = make_complete_report(
        df_res, f_rate, c_mass, d80, total_revenue, splitter_pos, 
        grid_data, x_labels, y_labels
    )
    
    st.download_button(
        label="📥 Download Full Executive Report (Word)",
        data=report_data,
        file_name="Spiral_Detailed_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="download_report_final"
    )
