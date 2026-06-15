import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from bs4 import BeautifulSoup
from config import OPENAI_API_KEY, FILINGS_DIR, CACHE_DIR

from llama_index.core import (
    VectorStoreIndex,
    Document,
    StorageContext,
    Settings
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb


def setup_llama_settings():
    Settings.llm = OpenAI(
        model="gpt-4o-mini",
        api_key=OPENAI_API_KEY,
        temperature=0.1
    )
    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=OPENAI_API_KEY
    )
    Settings.node_parser = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=50
    )
    print("✓ LlamaIndex configured with OpenAI")


def get_chroma_collection(ticker: str):
    """Get or create a ChromaDB collection for a ticker."""
    chroma_path = str(CACHE_DIR / "chroma_db")
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name=f"{ticker.lower()}_filings",
        metadata={"hnsw:space": "cosine"}
    )
    print(f"✓ ChromaDB ready — collection: {ticker.lower()}_filings")
    print(f"  Path: {chroma_path}")
    print(f"  Existing documents: {collection.count()}")
    return client, collection


def html_to_clean_text(html_path: Path) -> str:
    """Strip HTML tags and extract readable text from a 10-K filing."""
    raw_html = html_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def load_filing_documents(ticker: str) -> list:
    """Load and clean all HTML filings for a ticker."""
    filings_path = FILINGS_DIR / ticker
    if not filings_path.exists():
        raise FileNotFoundError(
            f"No filings found for {ticker}. Run filing_retrieval.py first."
        )

    html_files = sorted(filings_path.glob("*.html"))
    documents = []

    for f in html_files:
        print(f"  Cleaning: {f.name} ...")
        clean_text = html_to_clean_text(f)
        print(f"    → {len(clean_text):,} characters extracted")

        doc = Document(
            text=clean_text,
            metadata={
                "ticker":   ticker,
                "doc_type": "10-K",
                "source":   "SEC EDGAR",
                "filename": f.name
            }
        )
        documents.append(doc)

    return documents


def ingest_filings(ticker: str) -> VectorStoreIndex:
    """
    Load 10-K filings, embed them, store in ChromaDB locally.
    No cloud, no network issues — runs 100% on your machine.
    """
    print(f"\n{'='*55}")
    print(f"  RAG Pipeline — Ingesting {ticker} filings")
    print(f"  Vector Store: ChromaDB (local)")
    print(f"{'='*55}\n")

    setup_llama_settings()
    chroma_client, collection = get_chroma_collection(ticker)

    # Skip ingestion if already done
    if collection.count() > 0:
        print(f"✓ Already ingested {collection.count()} chunks — loading existing index")
        return load_existing_index(ticker)

    print(f"\nLoading and cleaning documents for {ticker}...")
    documents = load_filing_documents(ticker)
    print(f"✓ Loaded and cleaned {len(documents)} filing documents")

    # Build vector store
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )

    print(f"\nEmbedding and storing in ChromaDB...")
    print(f"  This takes 1-2 minutes for 3 filings...")

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True
    )

    print(f"\n✓ Successfully ingested {ticker} filings")
    print(f"  Total chunks stored: {collection.count()}")
    return index


def load_existing_index(ticker: str) -> VectorStoreIndex:
    """Load an already-ingested index from ChromaDB."""
    setup_llama_settings()
    chroma_client, collection = get_chroma_collection(ticker)

    vector_store    = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context
    )
    return index


def query_filings(ticker: str, question: str, index=None) -> str:
    """Ask a question about the company's filings using RAG."""
    if index is None:
        index = load_existing_index(ticker)

    query_engine = index.as_query_engine(
        similarity_top_k=5,
        verbose=False
    )

    print(f"\n  Q: {question}")
    response = query_engine.query(question)
    answer = str(response)
    print(f"  A: {answer[:400]}...")
    return answer


if __name__ == "__main__":
    ticker = "AAPL"

    # Ingest filings (skipped automatically if already done)
    index = ingest_filings(ticker)

    # Test RAG queries on real Apple 10-K filings
    questions = [
        "What was Apple's total revenue and net income for fiscal year 2025?",
        "What are the main risk factors Apple mentioned in their 2025 10-K?",
        "What did Apple say about their AI and machine learning strategy?",
    ]

    print(f"\n{'='*55}")
    print(f"  Testing RAG queries on {ticker} filings")
    print(f"{'='*55}")

    for q in questions:
        query_filings(ticker, q, index)
        print()

    print(f"\n{'='*55}")
    print(f"  RAG Pipeline Complete!")
    print(f"{'='*55}")