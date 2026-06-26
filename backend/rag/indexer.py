"""
SOP Document Indexer

Run this once before starting the server:
    python -m backend.rag.indexer

DESIGN DECISION: Local embeddings (sentence-transformers all-MiniLM-L6-v2) vs. API embeddings.

Using local embeddings means:
  PROS: No extra API key, no embedding API cost, runs offline, fast for < 1000 docs.
  CONS: Lower quality than text-embedding-3-large or Voyage AI. For a small, well-structured
        SOP corpus (~5 documents, ~50 chunks) the quality difference is negligible.

In production (large policy corpus, multilingual), switch to:
    from langchain_voyageai import VoyageAIEmbeddings  # Anthropic-affiliated, best quality
"""

import os
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma
from backend.config import settings

SOP_DOCS_DIR = Path(__file__).parent / "sop_docs"
COLLECTION_NAME = "sahayak_sop"


def get_embeddings():
    # FastEmbedEmbeddings uses ONNX runtime — no PyTorch dependency, no torch._dynamo conflicts
    return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")


def build_index():
    """Load SOP markdown files, split by headers, and index into ChromaDB."""
    print("Loading SOP documents...")
    loader = DirectoryLoader(
        str(SOP_DOCS_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    raw_docs = loader.load()

    # TRADEOFF: Header-aware splitting vs. fixed-size chunking.
    # Header splitting keeps policy sections semantically intact — a 300-token
    # chunk on "Section 3.2: Wrong Item Delivered" is far more retrievable than
    # a chunk that splits mid-section. Slightly larger chunks = fewer retrieved
    # chunks needed per query.
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "document"),
            ("##", "section"),
            ("###", "subsection"),
        ]
    )

    all_chunks = []
    for doc in raw_docs:
        chunks = header_splitter.split_text(doc.page_content)
        for chunk in chunks:
            chunk.metadata["source"] = doc.metadata.get("source", "unknown")
        all_chunks.extend(chunks)

    print(f"Split into {len(all_chunks)} chunks across {len(raw_docs)} documents.")

    embeddings = get_embeddings()
    vectorstore = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=settings.chroma_persist_dir,
    )
    print(f"Indexed {len(all_chunks)} chunks into ChromaDB at {settings.chroma_persist_dir}")
    return vectorstore


def get_vectorstore() -> Chroma:
    """Load existing index (call this at runtime, not build_index)."""
    embeddings = get_embeddings()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )


if __name__ == "__main__":
    build_index()
    print("Index built successfully.")
