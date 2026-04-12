"""
CompanyKB — Main Chat Interface
Run with: streamlit run app.py
"""
import streamlit as st
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.rag_engine import retrieve, get_stats, list_documents
from utils.llm_client import chat

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CompanyKB — Internal Knowledge Base",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark sidebar */
section[data-testid="stSidebar"] {
    background: #0f1117;
    border-right: 1px solid #1e2130;
}
section[data-testid="stSidebar"] * { color: #c9d1e0 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #ffffff !important; }

/* Main background */
.stApp { background: #f8f9fc; }

/* Chat messages */
.chat-msg {
    padding: 14px 18px;
    border-radius: 12px;
    margin-bottom: 12px;
    line-height: 1.6;
    font-size: 14px;
}
.user-msg {
    background: #1a56db;
    color: white;
    margin-left: 60px;
}
.bot-msg {
    background: white;
    color: #1e2130;
    border: 1px solid #e5e9f0;
    margin-right: 60px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.source-pill {
    display: inline-block;
    background: #f0f4ff;
    color: #3b5bdb;
    border: 1px solid #d0d9ff;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    margin: 4px 3px 0 0;
    font-weight: 500;
}
.stat-card {
    background: white;
    border: 1px solid #e5e9f0;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}
.stat-val { font-size: 28px; font-weight: 700; color: #1a56db; }
.stat-lbl { font-size: 12px; color: #6b7a99; margin-top: 2px; }

/* Hide streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Input box */
.stTextInput input {
    border-radius: 24px !important;
    border: 1.5px solid #d0d9ff !important;
    padding: 12px 18px !important;
    font-size: 14px !important;
}
.stTextInput input:focus {
    border-color: #1a56db !important;
    box-shadow: 0 0 0 3px rgba(26,86,219,0.12) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []   # for Claude API


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏢 CompanyKB")
    st.markdown("*Internal Knowledge Assistant*")
    st.divider()

    # Stats
    stats = get_stats()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Documents", stats["total_documents"])
    with col2:
        st.metric("Chunks", stats["total_chunks"])

    st.caption(f"**{stats['total_words']:,}** words indexed")

    # Category breakdown
    if stats["categories"]:
        st.divider()
        st.markdown("**📂 Categories**")
        for cat, count in sorted(stats["categories"].items()):
            st.markdown(f"<small>• {cat}: **{count}** doc{'s' if count > 1 else ''}</small>", unsafe_allow_html=True)

    st.divider()

    # Settings
    st.markdown("**⚙️ Settings**")
    top_k = st.slider("Chunks to retrieve", 2, 10, 5,
                      help="How many knowledge base excerpts to use per answer")
    show_sources = st.toggle("Show source excerpts", value=False)

    st.divider()
    st.markdown("**🔗 Navigation**")
    st.page_link("app.py", label="💬 Chat", icon="💬")
    st.page_link("pages/1_Admin_Upload.py", label="📤 Admin Upload", icon="📤")
    st.page_link("pages/2_Knowledge_Base.py", label="📚 Knowledge Base", icon="📚")

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history  = []
        st.rerun()


# ── Main chat area ────────────────────────────────────────────────────────────
st.markdown("## 💬 Ask anything about company policies & guides")
st.markdown("<small style='color:#6b7a99'>Answers are grounded in your uploaded documents — no hallucinations.</small>", unsafe_allow_html=True)
st.markdown("")

# Render existing messages
chat_container = st.container()
with chat_container:
    if not st.session_state.messages:
        st.markdown("""
        <div style='text-align:center; padding: 60px 20px; color:#6b7a99;'>
            <div style='font-size:48px; margin-bottom:16px'>🏢</div>
            <div style='font-size:16px; font-weight:600; color:#1e2130; margin-bottom:8px'>Welcome to CompanyKB</div>
            <div style='font-size:14px'>Ask me anything about HR policies, IT guides, sales materials, or company procedures.</div>
            <div style='margin-top:24px; display:flex; gap:10px; justify-content:center; flex-wrap:wrap;'>
        """, unsafe_allow_html=True)

        suggestions = [
            "What is the remote work policy?",
            "How do I submit an expense report?",
            "What are the IT security guidelines?",
            "How many vacation days do I get?",
        ]
        cols = st.columns(len(suggestions))
        for i, sug in enumerate(suggestions):
            with cols[i]:
                if st.button(sug, key=f"sug_{i}", use_container_width=True):
                    st.session_state.pending_query = sug
                    st.rerun()
    else:
        for msg in st.session_state.messages:
            css_class = "user-msg" if msg["role"] == "user" else "bot-msg"
            label = "**You**" if msg["role"] == "user" else "**CompanyKB**"
            st.markdown(f"""
            <div class="chat-msg {css_class}">
                <div style='font-size:11px; opacity:0.7; margin-bottom:4px'>{label}</div>
                {msg['content']}
            </div>
            """, unsafe_allow_html=True)

            if show_sources and msg["role"] == "assistant" and msg.get("chunks"):
                with st.expander(f"📎 {len(msg['chunks'])} source excerpt(s) used"):
                    for c in msg["chunks"]:
                        st.markdown(f"**{c['source']}** · score: `{c['score']}`")
                        st.markdown(f"> {c['text'][:300]}...")
                        st.divider()


# ── Input ─────────────────────────────────────────────────────────────────────
st.markdown("")
query = st.chat_input("Ask a question about company policies, HR, IT, sales...")

# Handle suggestion click
if "pending_query" in st.session_state:
    query = st.session_state.pop("pending_query")


def run_query(q: str):
    if not q.strip():
        return

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-key-here":
        st.error("⚠️ ANTHROPIC_API_KEY not set. Add it to your .env file and restart.")
        return

    # Check knowledge base has content
    stats = get_stats()
    if stats["total_documents"] == 0:
        st.warning("📭 No documents uploaded yet. Go to **Admin Upload** to add documents first.")
        return

    # Add user message to display
    st.session_state.messages.append({"role": "user", "content": q})

    # Retrieve relevant chunks
    chunks = retrieve(q, top_k=top_k)

    # Stream response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        with st.spinner("Searching knowledge base..."):
            for token in chat(q, chunks, st.session_state.history):
                full_response += token
                placeholder.markdown(full_response + "▌")
        placeholder.markdown(full_response)

    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "chunks": chunks,
    })
    st.session_state.history.append({"role": "user",      "content": q})
    st.session_state.history.append({"role": "assistant", "content": full_response})

    # Keep history to last 10 turns (20 messages) to manage tokens
    if len(st.session_state.history) > 20:
        st.session_state.history = st.session_state.history[-20:]

    st.rerun()


if query:
    run_query(query)
