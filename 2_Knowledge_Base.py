"""
Knowledge Base Browser — View all indexed documents and search chunks.
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.rag_engine import list_documents, retrieve, get_stats

st.set_page_config(
    page_title="Knowledge Base — CompanyKB",
    page_icon="📚",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #f8f9fc; }
#MainMenu, footer, header { visibility: hidden; }
.chunk-card {
    background: white;
    border: 1px solid #e5e9f0;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
    border-left: 4px solid #1a56db;
}
.score-bar {
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(90deg, #1a56db, #7c3aed);
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("## 📚 Knowledge Base Browser")
st.markdown("<small style='color:#6b7a99'>Browse all indexed documents or test retrieval with a search query.</small>", unsafe_allow_html=True)
st.markdown("")

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = get_stats()
c1, c2, c3 = st.columns(3)
c1.metric("Documents",    stats["total_documents"])
c2.metric("Chunks",       stats["total_chunks"])
c3.metric("Words Indexed", f"{stats['total_words']:,}")

st.divider()

tab1, tab2 = st.tabs(["📄 Documents", "🔍 Test Search"])

# ── Documents tab ──────────────────────────────────────────────────────────────
with tab1:
    docs = list_documents()
    if not docs:
        st.info("No documents in the knowledge base yet. Ask an admin to upload documents.")
    else:
        cats = ["All"] + sorted(set(d["category"] for d in docs))
        col_f, col_s = st.columns([2, 3])
        with col_f:
            filter_cat = st.selectbox("Category", cats)
        with col_s:
            search_docs = st.text_input("Search documents by name", placeholder="Type to filter...")

        filtered = docs
        if filter_cat != "All":
            filtered = [d for d in filtered if d["category"] == filter_cat]
        if search_docs:
            filtered = [d for d in filtered if search_docs.lower() in d["filename"].lower()]

        st.markdown(f"<small style='color:#6b7a99'>Showing {len(filtered)} of {len(docs)} documents</small>", unsafe_allow_html=True)
        st.markdown("")

        # Category legend
        cat_color = {
            "HR & People": "#10b981", "IT & Security": "#3b82f6",
            "Sales & Marketing": "#f59e0b", "Finance & Accounting": "#eab308",
            "Legal & Compliance": "#ef4444", "Operations": "#8b5cf6",
            "Product & Engineering": "#6b7280", "General": "#9ca3af",
        }

        for doc in sorted(filtered, key=lambda x: x["category"]):
            color = cat_color.get(doc["category"], "#6b7280")
            with st.container():
                st.markdown(f"""
                <div style='background:white; border:1px solid #e5e9f0; border-radius:10px;
                            padding:14px 16px; margin-bottom:10px;
                            border-left: 4px solid {color};'>
                    <div style='font-weight:600; font-size:14px; color:#1e2130'>📄 {doc['filename']}</div>
                    <div style='font-size:12px; color:#6b7a99; margin-top:4px'>
                        <span style='background:{color}22; color:{color}; border-radius:12px; padding:2px 8px; font-size:11px; font-weight:600'>{doc['category']}</span>
                        &nbsp; {doc['chunks']} chunks &nbsp;·&nbsp; {doc['words']:,} words
                        &nbsp;·&nbsp; {doc['size_kb']} KB &nbsp;·&nbsp; Uploaded {doc['uploaded'][:10]}
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ── Test Search tab ────────────────────────────────────────────────────────────
with tab2:
    st.markdown("Test how well the knowledge base retrieves content for a given question.")
    st.markdown("")

    col_q, col_k = st.columns([4, 1])
    with col_q:
        test_query = st.text_input("Enter a test query", placeholder="e.g. What is the parental leave policy?")
    with col_k:
        test_k = st.number_input("Top K", min_value=1, max_value=10, value=5)

    if st.button("🔍 Run Retrieval Test", type="primary") and test_query:
        with st.spinner("Searching..."):
            chunks = retrieve(test_query, top_k=test_k)

        if not chunks:
            st.warning("No relevant chunks found. Try a different query or upload more documents.")
        else:
            st.success(f"Found {len(chunks)} relevant excerpt(s)")
            st.markdown("")
            for i, chunk in enumerate(chunks, 1):
                score_pct = int(chunk["score"] * 1000)
                st.markdown(f"""
                <div class='chunk-card'>
                    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px'>
                        <div>
                            <span style='font-weight:600; font-size:13px'>Excerpt {i}</span>
                            &nbsp;
                            <span style='background:#f0f4ff; color:#3b5bdb; border-radius:12px; padding:2px 8px; font-size:11px'>
                                📄 {chunk['source']}
                            </span>
                        </div>
                        <span style='font-size:11px; color:#6b7a99'>Relevance: <strong>{chunk['score']:.4f}</strong></span>
                    </div>
                    <div class='score-bar' style='width:{min(score_pct, 100)}%'></div>
                    <p style='font-size:13px; color:#374151; margin-top:12px; line-height:1.6'>
                        {chunk['text'][:500]}{'...' if len(chunk['text']) > 500 else ''}
                    </p>
                    <div style='font-size:11px; color:#9ca3af; margin-top:8px'>
                        Chunk {chunk['chunk_idx']} of document {chunk['doc_id']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
