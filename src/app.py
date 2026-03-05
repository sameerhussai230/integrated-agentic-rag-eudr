import streamlit as st
import sys
import os
import yaml
import json
import folium
from pathlib import Path
from streamlit_folium import st_folium
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim

# Internal Modules
sys.path.append(str(Path(__file__).parent.parent))
from ingest import SatelliteIngestor
from process import WaterStressAnalyzer
from agent import audit_agent
from report_generator import create_full_report

# --- CONFIGURATION ---
st.set_page_config(page_title="Integrated Agentic RAG & Satellite System", page_icon="🛰️", layout="wide")

PRESETS = {
    "Amazon Rainforest (High Risk)": [-62.90, -10.50, -62.80, -10.40],
    "Harz Mountains, Germany (Degraded)": [10.60, 51.78, 10.68, 51.84],
    "Les Landes, France (Managed)": [-0.95, 44.15, -0.85, 44.25],
    "Tesla Gigafactory, Berlin (Urban)": [13.78, 52.38, 13.82, 52.41],
    "Białowieża Forest, Poland (Compliant)": [23.83, 52.72, 23.89, 52.76]
}

def load_config():
    with open("config/settings.yaml", "r") as f: return yaml.safe_load(f)

def load_data():
    data = {"meta": {}, "stats": {}}
    if Path("data/raw/metadata.json").exists():
        with open("data/raw/metadata.json") as f: data["meta"] = json.load(f)
    if Path("data/processed/stats.json").exists():
        with open("data/processed/stats.json") as f: data["stats"] = json.load(f)
    return data

config = load_config()
data = load_data()
meta = data["meta"]
stats = data["stats"]

if "agent_report" not in st.session_state:
    st.session_state["agent_report"] = None

# --- SIDEBAR ---
st.sidebar.title("EUDR Compliance 🛰️")
mode = st.sidebar.radio("Targeting Mode", ["Use Presets", "Global Search 🌍", "Coordinate Entry 📍"])

bbox = None
region_name = "Unknown"

if mode == "Use Presets":
    selected_preset = st.sidebar.selectbox("Select Region", list(PRESETS.keys()))
    bbox = PRESETS[selected_preset]
    region_name = selected_preset
elif mode == "Global Search 🌍":
    custom_loc = st.sidebar.text_input("Enter Location Name")
    if custom_loc:
        geolocator = Nominatim(user_agent="eudr_rag_system")
        loc = geolocator.geocode(custom_loc)
        if loc:
             bbox = [loc.longitude-0.05, loc.latitude-0.05, loc.longitude+0.05, loc.latitude+0.05]
             region_name = loc.address

today = datetime.now()
date_input = st.sidebar.date_input("Acquisition Window", value=(today - timedelta(days=60), today))
run_clicked = st.sidebar.button("🚀 Run Analysis", type="primary")

st.title("Integrated Agentic RAG & Satellite System for EUDR")
st.markdown(f"**Target Area:** {meta.get('region_name', region_name)}")

# --- MAIN TABS ---
tab1, tab2, tab3 = st.tabs(["🗺️ Geospatial Targeting", "👁️ Spectral Forensics", "⚖️ Compliance Report"])

with tab1:
    if run_clicked and bbox:
        with st.status("Initializing Autonomous Pipeline...", expanded=True) as status:
            dr = f"{date_input[0].strftime('%Y-%m-%d')}/{date_input[1].strftime('%Y-%m-%d')}"
            ingestor = SatelliteIngestor(config)
            
            st.write("📡 Tasking Sentinel-2 Satellite Constellation...")
            if ingestor.search_and_download(override_bbox=bbox, override_date=dr, override_name=region_name):
                
                st.write("🔬 Processing Multi-Spectral Telemetry...")
                analyzer = WaterStressAnalyzer()
                analyzer.run_parallel_pipeline()
                
                st.session_state["agent_report"] = None 
                status.update(label="Audit Complete", state="complete")
                st.rerun()
            else:
                st.error("No valid satellite imagery found for this timeframe/location.")
    
    m_loc = bbox if bbox else [2.35, 48.85, 2.45, 48.95]
    center = [(m_loc[1]+m_loc[3])/2, (m_loc[0]+m_loc[2])/2]
    m = folium.Map(location=center, zoom_start=11)
    if bbox: folium.Rectangle([[bbox[1], bbox[0]], [bbox[3], bbox[2]]], color="red", fill=True).add_to(m)
    st_folium(m, width=1400, height=400)

with tab2:
    if Path("data/processed/HighRes_Optical.png").exists():
        c1, c2 = st.columns(2)
        c1.image("data/processed/HighRes_Optical.png", caption="True-Color Optical Telemetry")
        c2.image("data/processed/HighRes_Analysis.png", caption="Spectral Deforestation Classification")
        
        if stats:
            st.info(f"Detected Vegetation Cover: {stats.get('vegetation_cover_pct')}% | Composite Stress Index: {stats.get('stress_pct')}%")

with tab3:
    if stats:
        st.subheader("🤖 AI Legal Compliance Agent")
        
        # Date Handling
        raw_date = meta.get('acquisition_date', datetime.now().isoformat())
        sat_date_str = raw_date[:10]

        if st.session_state["agent_report"] is None:
            with st.spinner("⚖️ Cross-referencing EUDR Articles 3, 9, and 24..."):
                agent_input = {
                    "geo_data": {
                        "status": stats.get('status'),
                        "stress_pct": stats.get('stress_pct'),
                        "vegetation_cover_pct": stats.get('vegetation_cover_pct'),
                        "date": sat_date_str
                    },
                    "legal_context": "",
                    "final_report": ""
                }
                try:
                    result = audit_agent.invoke(agent_input)
                    st.session_state["agent_report"] = result['final_report']
                except Exception as e:
                    st.error(f"Agent Error: {e}")

        if st.session_state["agent_report"]:
            # PDF Generation
            pdf_path = "data/processed/EUDR_Audit_Report.pdf"
            create_full_report(
                pdf_path, 
                st.session_state["agent_report"], 
                stats, 
                meta.get('region_name'),
                sat_date_str 
            )
            
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📄 Download Official Forensic Audit (PDF)",
                    data=f,
                    file_name=f"EUDR_Audit_{sat_date_str}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            
            st.markdown("---")
            st.markdown(st.session_state["agent_report"])