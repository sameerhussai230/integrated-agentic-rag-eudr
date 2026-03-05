import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from knowledge_base import get_vector_store

load_dotenv()

# --- INITIALIZATION ---
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("❌ GROQ_API_KEY is missing. Please check .env file.")

llm = ChatGroq(
    temperature=0.1, 
    model_name="llama-3.3-70b-versatile", 
    api_key=api_key
)

class AuditState(TypedDict):
    """State management for the RAG workflow."""
    geo_data: dict      
    legal_context: str  
    final_report: str   

def legal_research_node(state: AuditState):
    """Retrieves relevant EUDR articles based on risk level."""
    stress_pct = state['geo_data'].get('stress_pct', 0)
    db = get_vector_store()
    
    # 1. Base Legal Definitions (Article 2)
    results = db.similarity_search("Article 2 definitions deforestation forest degradation", k=2)
    
    # 2. Dynamic Retrieval based on Risk
    if stress_pct > 15:
        results += db.similarity_search("Article 3 prohibition market access non-compliance", k=2)
    else:
        results += db.similarity_search("Article 9 due diligence statement risk assessment", k=2)
    
    context = ""
    for doc in results:
        src = doc.metadata.get('source_file', 'EU Regulation')
        context += f"\n[SOURCE: {src}]\n{doc.page_content}\n"
    
    return {"legal_context": context}

def report_drafting_node(state: AuditState):
    """Synthesizes satellite data and legal context into a journal-grade report."""
    stats = state['geo_data']
    
    system_prompt = """You are the Chief EUDR Compliance Auditor for the European Commission.
    You are writing a formal "Deforestation Due Diligence Statement" for publication in an official legal journal.

    --- TONE & STYLE ---
    1. **Authoritative & Forensic:** Use professional terminology (e.g., "Pursuant to...", "Constitutes a breach of...").
    2. **Elegant Citation Flow:** Define the law ONCE at the start: "Regulation (EU) 2023/1115 ('The Regulation')". Thereafter, refer to articles naturally.
    3. **Evidence-Based:** Connect the Satellite Data directly to the Law.

    --- REPORT STRUCTURE ---
    # 1. Executive Compliance Abstract
    (A 3-line summary of the verdict. State clearly if the land is compliant or non-compliant.)

    # 2. Forensic Geospatial Analysis
    (Analyze the metrics: Stress Index and Vegetation Cover. Explain that 'Composite Stress' > 20% indicates degradation.)

    # 3. Regulatory Assessment
    (Apply the Law to the Evidence. Cite Article 3 (Prohibition) and Article 2 (Definitions).)

    # 4. Remediation & Directives
    (Instructions to the operator. If Non-Compliant: Immediate prohibition of market access. If Compliant: Maintain monitoring.)
    """
    
    user_prompt = f"""
    --- EVIDENTIARY DATA ---
    Target Date: {stats.get('date')}
    Composite Stress Index: {stats.get('stress_pct')}% (Threshold: 20.0%)
    Vegetation Cover: {stats.get('vegetation_cover_pct')}%
    Current Status: {stats.get('status')}
    
    --- LEGAL CONTEXT ---
    {state['legal_context']}
    
    --- INSTRUCTION ---
    Draft the full text for the "Formal Due Diligence Statement".
    """
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    return {"final_report": response.content}

# --- WORKFLOW GRAPH ---
workflow = StateGraph(AuditState)
workflow.add_node("legal_research", legal_research_node)
workflow.add_node("report_writer", report_drafting_node)
workflow.add_edge(START, "legal_research")
workflow.add_edge("legal_research", "report_writer")
workflow.add_edge("report_writer", END)

audit_agent = workflow.compile()