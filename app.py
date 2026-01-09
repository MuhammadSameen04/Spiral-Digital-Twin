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

# ----------- ADDITION: ECONOMICS / OPEX (NO CHANGE ABOVE) -----------
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

# ----------- ADDITION: KPI EVALUATION -----------



# ----------- ADDITION: KPI TARGETS (SIDEBAR ONLY) -----------
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
    # Variables for heatmap axis
    rates = np.linspace(100, 500, 10)  # Feed Rate range
    splits = np.linspace(0, 2, 10)     # Splitter range
    grid = np.zeros((10, 10))

    for i, r in enumerate(rates):
        for j, s in enumerate(splits):
            # Engine ko call karke profit nikalna
            _, _, total_rev = ultra_engine(r, targets, prices, s, d80)
            
            # OPEX Calculate karna usi logic se jo aapne niche likhi hai
            p_cost = power_kw * power_rate
            m_cost_hr = r * mining_cost
            total_opex = labour_cost + p_cost + water_cost + maintenance_cost + m_cost_hr + lease_tax
            
            grid[i, j] = total_rev - total_opex
            
    return grid, rates, splits

# ----------- ADDITION: ECONOMICS CALCULATION -----------
power_cost = power_kw * power_rate
mining_cost_hr = f_rate * mining_cost

total_opex = (
    labour_cost +
    power_cost +
    water_cost +
    maintenance_cost +
    mining_cost_hr +
    lease_tax
)

profit_hr = total_revenue - total_opex
actual_margin = (profit_hr / total_revenue) * 100 if total_revenue > 0 else 0

kpi_status = {
    "Throughput OK": f_rate >= target_throughput,
   "Profit Margin OK": actual_margin >= target_margin,
    "Profit/hr OK": profit_hr >= target_profit_hr
}
cost_per_ton = total_opex / f_rate
profit_per_ton = profit_hr / f_rate

# --- 5. TABS ---
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

    fig3, ax3 = plt.subplots()
    ax3.bar(["Revenue", "OPEX", "Profit"], [total_revenue, total_opex, profit_hr])
    ax3.set_ylabel("$/hr")
    st.pyplot(fig3)

with tab_theory:
    st.subheader("📚 Engineering Logic")
    st.latex(r"M_{feed} = M_{conc} + M_{midd} + M_{tail}")
    st.latex(r"Mass\_Pull = 10\% + (Splitter\_Position \times 10\%)")
    st.info(f"Operating at {f_rate} tph with splitter position {splitter_pos}")

with tab_export:
    def make_report(df, rate, conc_m, d80_v, total_r, split_p):
        doc = Document()
        doc.add_heading('Engineering Report: Spiral Digital Twin', 0)
        doc.add_paragraph(f"Feed: {rate} tph | d80: {d80_v} um | Splitter: {split_p}")
        
        fig_r, ax_r = plt.subplots()
        ax_r.pie(df["Revenue $/hr"], labels=df["Mineral"], autopct='%1.1f%%')
        img_s = BytesIO()
        plt.savefig(img_s, format='png')
        img_s.seek(0)
        doc.add_picture(img_s, width=Inches(5))
        
        t = doc.add_table(rows=1, cols=len(df.columns))
        t.style = 'Table Grid'
        for i, col in enumerate(df.columns):
            t.cell(0, i).text = col
        for _, row in df.iterrows():
            cells = t.add_row().cells
            for i, val in enumerate(row):
                cells[i].text = str(val)
        
        bio = BytesIO()
        doc.save(bio)
        return bio.getvalue()

st.write("---")
st.subheader("🔥 Profitability Heatmap (Feed Rate vs Splitter)")

# Data generate karna
grid_data, x_labels, y_labels = generate_heatmap_data(user_targets, user_prices, d80, solids)

# Plotting
fig_heat, ax_heat = plt.subplots(figsize=(10, 6))
sns.heatmap(
    grid_data, 
    annot=False, 
    xticklabels=np.round(y_labels, 1), 
    yticklabels=np.round(x_labels, 0), 
    cmap="RdYlGn", 
    ax=ax_heat
)
ax_heat.set_xlabel("Splitter Position")
ax_heat.set_ylabel("Feed Rate (tph)")
st.pyplot(fig_heat)

st.info("💡 **Tip:** Green area sab se zyada profit dikhata hai. Red area ka matlab hai ke aapka OPEX revenue se zyada hai.")

   # --- Is niche wale block ko check karein aur "key" add karein ---
st.download_button(
    label="📥 Download Full Executive Report (Word)",
    data=make_report(df_res, f_rate, c_mass, d80, total_revenue, splitter_pos),
    file_name="Spiral_Digital_Twin_Report.docx",
    key="final_report_button",
) # <--- Ye bracket lazmi hai!

st.markdown("### 🧠 KPI Status Check")

for k, v in kpi_status.items():
    if v:
        st.success(f"✅ {k}")
    else:
        st.error(f"❌ {k}")

