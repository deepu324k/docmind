"""
Embedder — Generate embeddings using HuggingFace sentence-transformers
and manage FAISS indexes per session.
"""

import os
import json
import numpy as np
import faiss
from fastembed import TextEmbedding

# Global model instance (loaded once)
_model = None

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")


def _get_model():
    """Load the fastembed model (singleton)."""
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _model


def generate_embeddings(texts):
    """Generate embeddings for a list of texts."""
    model = _get_model()
    embeddings = list(model.embed(texts))
    return np.array(embeddings, dtype="float32")


def create_index(chunks, session_id):
    """
    Create a FAISS index from chunks and persist to disk.
    chunks: list of dicts with 'text', 'doc_name', 'page', 'chunk_id'
    """
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    texts = [c["text"] for c in chunks]
    embeddings = generate_embeddings(texts)

    # Build FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # Save FAISS index
    faiss.write_index(index, os.path.join(session_dir, "index.faiss"))

    # Save chunk metadata
    metadata = []
    for c in chunks:
        metadata.append({
            "doc_name": c["doc_name"],
            "page": c["page"],
            "text": c["text"],
            "chunk_id": c["chunk_id"]
        })

    with open(os.path.join(session_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    return len(chunks)


def add_to_index(new_chunks, session_id):
    """
    Add new chunks to an existing FAISS index (for multi-doc uploads).
    """
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    index_path = os.path.join(session_dir, "index.faiss")
    meta_path = os.path.join(session_dir, "metadata.json")

    if not os.path.exists(index_path):
        return create_index(new_chunks, session_id)

    # Load existing
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Generate new embeddings
    texts = [c["text"] for c in new_chunks]
    embeddings = generate_embeddings(texts)

    # Add to index
    index.add(embeddings)

    # Update metadata
    for c in new_chunks:
        metadata.append({
            "doc_name": c["doc_name"],
            "page": c["page"],
            "text": c["text"],
            "chunk_id": c["chunk_id"]
        })

    # Save updated
    faiss.write_index(index, index_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    return len(new_chunks)


def load_index(session_id):
    """Load a persisted FAISS index and metadata."""
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    index_path = os.path.join(session_dir, "index.faiss")
    meta_path = os.path.join(session_dir, "metadata.json")

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        raise FileNotFoundError(f"No index found for session {session_id}")

    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return index, metadata


def embed_query(query):
    """Embed a single query string."""
    model = _get_model()
    embedding = list(model.embed([query]))
    return np.array(embedding, dtype="float32")
