# DocuMind 🧠📄

**AI Document Intelligence & RAG Chat System**

DocuMind lets you upload PDF documents and ask questions about them using AI. It uses Retrieval-Augmented Generation (RAG) to find the most relevant passages from your documents and generates accurate, cited answers powered by the Groq LLM API.

---

## Features

- 📤 Upload multiple PDF documents
- 💬 Chat with your documents using natural language
- 🔍 RAG-based retrieval with semantic search (FAISS + sentence-transformers)
- 🤖 AI answers powered by Groq (`llama-3.1-8b-instant`)
- 📌 Source citations with document name and page number
- 🗂️ Session management — keep multiple document chats organized
- 🌐 Deployable to Railway, Render, or any cloud platform

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| PDF Parsing | PyMuPDF |
| Embeddings | sentence-transformers |
| Vector Search | FAISS |
| LLM | Groq API (llama-3.1-8b-instant) |
| Database | SQLite |
| Deployment | Gunicorn + Railway |

---

## Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/documind.git
cd documind
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=your_secret_key_here
PORT=5000
```
Get a free Groq API key at https://console.groq.com

### 4. Run the app
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser.

---

## Deploy to Railway

1. Push this repo to GitHub
2. Go to https://railway.app → **New Project → Deploy from GitHub repo**
3. Select this repository
4. In Railway **Variables** tab, add:
   - `GROQ_API_KEY` = your Groq API key
   - `SECRET_KEY` = any random string
5. Railway will build and deploy automatically — you'll get a live public URL

---

## Usage

1. Click **New Session** to start a chat
2. Upload one or more PDF files
3. Type your question in the chat box
4. DocuMind will answer with citations from your documents

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for LLM answers |
| `SECRET_KEY` | Yes | Flask session secret key |
| `PORT` | No | Server port (default: 5000) |

---

## License

MIT License
