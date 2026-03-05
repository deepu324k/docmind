"""
DocuMind — AI Document Intelligence & RAG Chat System
Main Flask application with all API routes.
"""

import os
import uuid
import tempfile
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables from the project directory
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

from core.pdf_parser import parse_pdf, chunk_text, extract_tables
from core.embedder import create_index, add_to_index
from core.retriever import retrieve
from core.llm import generate_answer
from core.db import init_db, create_session, get_session, save_chat, get_history, get_all_sessions, update_session_docs

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "documind-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max upload

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── Routes ───────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the frontend."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """
    Upload PDF file(s), parse, embed, and index them.
    Returns session_id, doc_names, and any extracted table data.
    """
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files selected"}), 400

    # Check if adding to existing session
    session_id = request.form.get("session_id") or str(uuid.uuid4())
    existing_session = get_session(session_id)

    doc_names = []
    all_chunks = []
    all_table_data = {}

    for file in files:
        if not file or not file.filename:
            continue

        if not allowed_file(file.filename):
            return jsonify({"error": f"Invalid file type: {file.filename}. Only PDFs are allowed."}), 400

        filename = secure_filename(file.filename)
        doc_names.append(filename)

        # Save to temp file for processing
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)

        try:
            # Parse PDF
            pages = parse_pdf(temp_path)

            # Chunk text
            chunks = chunk_text(pages, filename)
            all_chunks.extend(chunks)

            # Extract tables/structured data
            table_info = extract_tables(temp_path)
            if table_info["tables"] or table_info["structured_fields"]:
                all_table_data[filename] = table_info

        except ValueError as e:
            return jsonify({"error": str(e)}), 422
        except Exception as e:
            return jsonify({"error": f"Error processing {filename}: {str(e)}"}), 500
        finally:
            # Clean up temp file
            try:
                os.remove(temp_path)
                os.rmdir(temp_dir)
            except OSError:
                pass

    if not all_chunks:
        return jsonify({"error": "No text could be extracted from the uploaded files."}), 422

    try:
        # Create or update FAISS index
        if existing_session:
            num_chunks = add_to_index(all_chunks, session_id)
            existing_docs = existing_session["doc_names"]
            all_doc_names = existing_docs + doc_names
            update_session_docs(session_id, all_doc_names, all_table_data or None)
        else:
            num_chunks = create_index(all_chunks, session_id)
            all_doc_names = doc_names
            create_session(session_id, doc_names, all_table_data or None)

        return jsonify({
            "session_id": session_id,
            "doc_names": all_doc_names,
            "num_chunks": num_chunks,
            "table_data": all_table_data if all_table_data else None,
            "message": f"Successfully processed {len(doc_names)} document(s) into {num_chunks} chunks."
        })

    except Exception as e:
        return jsonify({"error": f"Error creating index: {str(e)}"}), 500


@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat with uploaded documents.
    Accepts {session_id, question}, returns {answer, sources}.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    session_id = data.get("session_id")
    question = data.get("question", "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    if not question:
        return jsonify({"error": "question is required"}), 400

    # Verify session exists
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found. Please upload a document first."}), 404

    try:
        # Retrieve relevant chunks
        context_chunks = retrieve(question, session_id, top_k=5)

        if not context_chunks:
            return jsonify({
                "answer": "I couldn't find any relevant information in the uploaded documents for your question.",
                "sources": []
            })

        # Generate answer
        result = generate_answer(question, context_chunks)

        # Save to chat history
        save_chat(session_id, question, result["answer"], result["sources"])

        return jsonify(result)

    except FileNotFoundError:
        return jsonify({"error": "Session index not found. Please re-upload your documents."}), 404
    except Exception as e:
        return jsonify({"error": f"Error generating answer: {str(e)}"}), 500


@app.route("/history/<session_id>")
def history(session_id):
    """Return full chat history for a session."""
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    chat_history = get_history(session_id)
    return jsonify({
        "session": session,
        "history": chat_history
    })


@app.route("/sessions")
def sessions():
    """Return all sessions."""
    all_sessions = get_all_sessions()
    return jsonify({"sessions": all_sessions})


# ─── Error Handlers ──────────────────────────────────────────────────────────


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 50MB."}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ─── Main ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
