import os
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Point to the data folder
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data" / "chroma_db"

def get_vector_store():
    """
    Returns the persistent Vector Store instance.
    """
    # Safety Check
    if not DB_DIR.exists() or not (DB_DIR / "chroma.sqlite3").exists():
        raise FileNotFoundError(
            "❌ Vector DB not found! Please run 'python src/setup_knowledge.py' first."
        )
        
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    return Chroma(
        collection_name="eudr_regulations",
        embedding_function=embedding_function,
        persist_directory=str(DB_DIR)
    )