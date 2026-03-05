"""
Retriever — Search FAISS index for top-k relevant chunks given a query.
"""

from core.embedder import load_index, embed_query


def retrieve(query, session_id, top_k=5):
    """
    Retrieve top-k most relevant chunks for a query from the session's FAISS index.
    Returns list of dicts: [{doc_name, page, text, score}]
    """
    index, metadata = load_index(session_id)

    # Embed the query
    query_embedding = embed_query(query)

    # Clamp top_k to available chunks
    actual_k = min(top_k, index.ntotal)
    if actual_k == 0:
        return []

    # Search
    distances, indices = index.search(query_embedding, actual_k)

    results = []
    seen_texts = set()

    for i, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue

        chunk = metadata[idx]
        # Deduplicate very similar chunks
        text_key = chunk["text"][:100]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        results.append({
            "doc_name": chunk["doc_name"],
            "page": chunk["page"],
            "text": chunk["text"],
            "score": float(distances[0][i])
        })

    return results
