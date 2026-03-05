# Integrated Agentic RAG & Satellite System for EUDR Legal Compliance

**An AI-driven geospatial framework for automating compliance with the European Union Deforestation Regulation (EUDR).**

![Python](https://img.shields.io/badge/python-3.11-green)

## 📖 Abstract
GeoTrace-EUDR automates the "Due Diligence" process required by **Regulation (EU) 2023/1115**. By integrating Sentinel-2 satellite telemetry with a Retrieval-Augmented Generation (RAG) Legal Agent, the system provides:
1.  **Forensic Land Analysis:** Multi-spectral classification (NDVI, GNDVI, NDWI) to detect forest degradation.
2.  **Legal Reasoning:** Automated drafting of compliance statements referencing specific EU Articles (3, 9, 24).
3.  **Audit Generation:** Creation of journal-grade forensic PDF reports.

## 🏗️ System Architecture

```mermaid
graph TD
    User[User Input: Region & Date] -->|Trigger| App[Streamlit Interface]
    
    subgraph "Data Acquisition Layer"
        App -->|Query| STAC[Microsoft Planetary Computer]
        STAC -->|Download L2A| Raw[Raw Satellite Bands]
    end
    
    subgraph "Processing Core"
        Raw -->|ThreadPool| Process[WaterStressAnalyzer]
        Process -->|Calc Indices| NDVI[Vegetation Health]
        Process -->|Calc Indices| Stress[Stress Index]
        Stress -->|JSON Stats| Metrics[Forensic Metrics]
    end
    
    subgraph "Legal Intelligence Agent"
        Metrics -->|Input| Agent[LangGraph Agent]
        KB[(ChromaDB: EUDR Laws)] -->|Retrieve Context| Agent
        Agent -->|LLM Inference| Draft[Legal Verdict]
    end
    
    subgraph "Reporting Layer"
        Draft -->|Format| PDF[PDF Report Generator]
        Process -->|HighRes Img| PDF
        PDF -->|Download| Final[Forensic Audit Report.pdf]
    end
