# 🏢 CompanyKB — Internal Knowledge Base Chatbot

A secure, RAG-powered internal knowledge base chatbot built with Python and Streamlit. Employees can ask natural language questions about company policies, HR documents, IT guides, and sales materials. Admins can upload documents through a password-protected interface.

---

## Features

- **RAG-powered answers** — retrieves relevant document excerpts before answering; no hallucinations
- **Multi-format ingestion** — PDF, DOCX, TXT, Markdown
- **Admin upload panel** — password-protected, categorized document management
- **Knowledge base browser** — view all indexed docs, test retrieval queries
- **Streaming responses** — answers appear token by token like a real chatbot
- **Source citations** — every answer cites which documents were used
- **Conversation memory** — maintains context across a session (last 10 turns)
- **Docker-ready** — one command to deploy on any internal cloud

---

## Tech Stack

| Layer | Tool |
|---|---|
| Frontend | Streamlit |
| LLM | Anthropic Claude (claude-sonnet) |
| Vector Search | TF-IDF + Cosine Similarity (built-in, no GPU needed) |
| Document Parsing | PyPDF2, python-docx |
| Deployment | Docker + Docker Compose |

---

## Quick Start (Local)

### 1. Clone and enter project
```bash
git clone <your-repo-url>
cd company-kb
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\Activate.ps1    # Windows PowerShell
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and set your `ANTHROPIC_API_KEY`. Get one at https://console.anthropic.com

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
ADMIN_PASSWORD=your-secure-password
```

### 5. Load the .env variables
```bash
# macOS/Linux
export $(cat .env | xargs)

# Windows PowerShell
Get-Content .env | ForEach-Object { $k,$v = $_ -split '=',2; [System.Environment]::SetEnvironmentVariable($k,$v) }
```

### 6. Seed sample documents (optional)
```bash
python seed_sample_docs.py
```

### 7. Run the app
```bash
streamlit run app.py
```
Open http://localhost:8501

---

## Uploading Documents

1. Go to **Admin Upload** in the sidebar
2. Enter the admin password (default: `admin123` — change this in `.env`)
3. Select a category, drag and drop files, click **Ingest**
4. Documents are immediately searchable in the chat

Supported formats: **PDF, DOCX, TXT, Markdown**

---

## Docker Deployment (Internal Cloud)

### Build and run
```bash
# Set your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "ADMIN_PASSWORD=your-secure-password" >> .env

# Build and start
docker-compose up -d
```
Access at http://your-server-ip:8501

### Useful Docker commands
```bash
docker-compose logs -f          # View logs
docker-compose down             # Stop
docker-compose up -d --build    # Rebuild after code changes
docker-compose ps               # Check status
```

Documents and the vector store are persisted in Docker volumes — safe across restarts.

---

## Project Structure

```
company-kb/
├── app.py                          # Main chat interface
├── pages/
│   ├── 1_Admin_Upload.py           # Document upload (password-protected)
│   └── 2_Knowledge_Base.py         # Browse docs + test search
├── utils/
│   ├── rag_engine.py               # RAG core: chunking, TF-IDF, retrieval
│   └── llm_client.py               # Anthropic Claude API wrapper
├── sample_docs/                    # Sample documents for demo
├── documents/                      # Uploaded documents (auto-created)
├── vector_store/                   # Index + metadata (auto-created)
├── .streamlit/config.toml          # Streamlit theme config
├── seed_sample_docs.py             # One-time sample data loader
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Upgrading to Semantic Search (Optional)

The current engine uses TF-IDF which works well and requires no GPU. To upgrade to semantic embeddings (better for conceptual questions):

1. Uncomment `sentence-transformers` in `requirements.txt`
2. In `rag_engine.py`, replace the `TFIDFStore` with a `sentence-transformers` + `faiss` implementation

---

## Security Notes

- Change `ADMIN_PASSWORD` from the default before deploying
- Keep `ANTHROPIC_API_KEY` secret — never commit `.env` to version control
- For production, add SSO/LDAP authentication in front of Streamlit
- The Docker setup runs on an internal port — do not expose directly to the internet without a reverse proxy (nginx) and HTTPS

---

## License

Internal use only.
