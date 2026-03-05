"""
LLM — Generate answers using Groq API (primary) or HuggingFace Inference API (fallback).
"""

import os
import json
import requests

def _get_groq_key():
    return os.environ.get("GROQ_API_KEY", "")

def _get_hf_token():
    return os.environ.get("HF_API_TOKEN", "")

GROQ_API_KEY = _get_groq_key()
HF_API_TOKEN = _get_hf_token()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
HF_API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"


def generate_answer(question, context_chunks):
    """
    Generate an answer using retrieved context chunks.
    Returns dict: {answer: str, sources: [{doc, page}]}
    """
    # Build context from chunks
    context_parts = []
    sources = []
    seen_sources = set()

    for chunk in context_chunks:
        context_parts.append(
            f"[Source: {chunk['doc_name']}, Page {chunk['page']}]\n{chunk['text']}"
        )
        source_key = (chunk["doc_name"], chunk["page"])
        if source_key not in seen_sources:
            sources.append({"doc": chunk["doc_name"], "page": chunk["page"]})
            seen_sources.add(source_key)

    context = "\n\n---\n\n".join(context_parts)

    # Try Groq first, then HuggingFace (read keys at call time)
    groq_key = _get_groq_key()
    hf_token = _get_hf_token()

    answer = None
    if groq_key:
        answer = _call_groq(question, context, groq_key)

    if answer is None and hf_token:
        answer = _call_huggingface(question, context, hf_token)

    if answer is None:
        answer = _generate_extractive_answer(question, context_chunks)

    return {
        "answer": answer,
        "sources": sources
    }


def _call_groq(question, context, groq_key=None):
    """Call Groq API with llama3-8b-8192."""
    if groq_key is None:
        groq_key = _get_groq_key()
    try:
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }

        system_prompt = (
            "You are DocuMind, an AI assistant that answers questions based ONLY on the provided document context. "
            "Always cite which document and page number your answer comes from. "
            "If the context doesn't contain enough information to answer, say so clearly. "
            "Be concise but thorough."
        )

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context from uploaded documents:\n\n{context}\n\n---\n\nQuestion: {question}\n\nAnswer based on the context above, citing document name and page numbers:"}
            ],
            "temperature": 0.3,
            "max_tokens": 1024
        }

        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print(f"Groq API error: {e}")
        return None


def _call_huggingface(question, context, hf_token=None):
    """Call HuggingFace Inference API with flan-t5-base."""
    if hf_token is None:
        hf_token = _get_hf_token()
    try:
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }

        # Truncate context for flan-t5 (smaller context window)
        truncated_context = context[:2000]

        payload = {
            "inputs": f"Based on the following context, answer the question.\n\nContext: {truncated_context}\n\nQuestion: {question}\n\nAnswer:",
            "parameters": {
                "max_new_tokens": 512,
                "temperature": 0.3
            }
        }

        response = requests.post(HF_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("generated_text", "")
        return str(data)

    except Exception as e:
        print(f"HuggingFace API error: {e}")
        return None


def _generate_extractive_answer(question, context_chunks):
    """
    Fallback: Generate a simple extractive answer when no LLM API is available.
    Returns the most relevant chunks as the answer.
    """
    if not context_chunks:
        return "I couldn't find relevant information in the uploaded documents to answer your question."

    answer_parts = ["Based on the uploaded documents, here are the most relevant passages:\n"]

    for i, chunk in enumerate(context_chunks[:3], 1):
        answer_parts.append(
            f"**{i}. From {chunk['doc_name']}, Page {chunk['page']}:**\n"
            f"{chunk['text'][:300]}{'...' if len(chunk['text']) > 300 else ''}\n"
        )

    answer_parts.append(
        "\n*Note: No LLM API key configured. Set GROQ_API_KEY or HF_API_TOKEN for AI-generated answers.*"
    )

    return "\n".join(answer_parts)
