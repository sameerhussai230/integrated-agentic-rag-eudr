import os
import shutil
import re
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data" / "chroma_db"
PDF_DIR = BASE_DIR / "data" / "legal_docs"

TARGET_FILES = [
    {"filename": "EUDR_Regulation_2023_1115.pdf", "category": "legal_text"},
    {"filename": "EUDR_Guidance_2025.pdf", "category": "guidance"}
]

def build_vector_db():
    print("⚡ STARTING KNOWLEDGE BASE BUILDER")
    
    if not PDF_DIR.exists():
        print(f"❌ Error: Folder not found: {PDF_DIR}")
        return

    # Check for files
    for doc in TARGET_FILES:
        fpath = PDF_DIR / doc['filename']
        if not fpath.exists():
            print(f"❌ MISSING FILE: {doc['filename']}")
            return

    # Reset Database
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)
        print("🧹 Cleared old database cache.")
    
    DB_DIR.mkdir(parents=True, exist_ok=True)

    # Ingestion
    print("\n🔄 Processing PDFs...")
    all_splits = []
    
    for doc in TARGET_FILES:
        fpath = PDF_DIR / doc['filename']
        print(f"📄 Reading: {doc['filename']}...")
        
        try:
            loader = PyPDFLoader(str(fpath))
            raw_docs = loader.load()
            
            for d in raw_docs:
                d.page_content = re.sub(r'L \d+/\d+.*?EN', '', d.page_content)
                d.metadata["category"] = doc["category"]
                d.metadata["source_file"] = doc["filename"]

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, 
                chunk_overlap=150,
                separators=["\nArticle", "\n\n", ". ", " "]
            )
            splits = text_splitter.split_documents(raw_docs)
            all_splits.extend(splits)
            print(f"   -> Extracted {len(splits)} chunks.")
            
        except Exception as e:
            print(f"   ⚠️ Error parsing {doc['filename']}: {e}")

    # Create DB
    if all_splits:
        print("\n💾 Generating Embeddings...")
        embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        Chroma.from_documents(
            documents=all_splits,
            embedding=embedding_function,
            persist_directory=str(DB_DIR),
            collection_name="eudr_regulations"
        )
        print("✅ SUCCESS: Knowledge Base is ready!")
    else:
        print("❌ CRITICAL: No text extracted.")

if __name__ == "__main__":
    build_vector_db()