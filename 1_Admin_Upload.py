"""
Admin Upload Page — Secure document management interface.
"""
import streamlit as st
import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.rag_engine import ingest_document, delete_document, list_documents, get_stats, DOCUMENTS_PATH

st.set_page_config(
    page_title="Admin Upload — CompanyKB",
    page_icon="📤",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #f8f9fc; }
#MainMenu, footer, header { visibility: hidden; }
.upload-zone {
    border: 2px dashed #d0d9ff;
    border-radius: 14px;
    padding: 32px;
    text-align: center;
    background: #f5f8ff;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)


# ── Admin auth (simple password gate) ────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if not st.session_state.admin_authed:
    st.markdown("## 🔐 Admin Access")
    st.markdown("This area is restricted to administrators.")
    pw = st.text_input("Enter admin password", type="password")
    if st.button("Login", type="primary"):
        if pw == ADMIN_PASSWORD:
            st.session_state.admin_authed = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ── Authenticated ─────────────────────────────────────────────────────────────
st.markdown("## 📤 Document Upload")
st.markdown("<small style='color:#6b7a99'>Upload company documents to the knowledge base. Supported: PDF, DOCX, TXT, MD</small>", unsafe_allow_html=True)
st.markdown("")

# ── Stats row ─────────────────────────────────────────────────────────────────
stats = get_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Documents", stats["total_documents"])
c2.metric("Total Chunks",    stats["total_chunks"])
c3.metric("Words Indexed",   f"{stats['total_words']:,}")
c4.metric("Categories",      len(stats["categories"]))

st.divider()

# ── Upload section ────────────────────────────────────────────────────────────
col_up, col_list = st.columns([1, 1], gap="large")

with col_up:
    st.markdown("### ➕ Add Documents")

    category = st.selectbox("Document Category", [
        "HR & People",
        "IT & Security",
        "Sales & Marketing",
        "Finance & Accounting",
        "Legal & Compliance",
        "Operations",
        "Product & Engineering",
        "General",
    ])

    uploaded_files = st.file_uploader(
        "Drop files here or click to browse",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        help="Maximum 50MB per file. Supported: PDF, DOCX, TXT, Markdown",
    )

    if uploaded_files:
        if st.button(f"⚡ Ingest {len(uploaded_files)} file(s)", type="primary", use_container_width=True):
            DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
            progress = st.progress(0)
            results  = []

            for i, uf in enumerate(uploaded_files):
                with st.spinner(f"Processing {uf.name}..."):
                    # Save to temp then process
                    suffix = Path(uf.name).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uf.read())
                        tmp_path = Path(tmp.name)

                    # Rename to original filename for display
                    final_path = DOCUMENTS_PATH / uf.name
                    tmp_path.rename(final_path)

                    try:
                        entry = ingest_document(final_path, category=category)
                        results.append(("✅", uf.name, entry["chunks"], entry["words"]))
                    except Exception as e:
                        results.append(("❌", uf.name, 0, str(e)))

                progress.progress((i + 1) / len(uploaded_files))

            st.success(f"Ingestion complete!")
            for icon, name, chunks, detail in results:
                if icon == "✅":
                    st.markdown(f"{icon} **{name}** — {chunks} chunks, {detail:,} words")
                else:
                    st.markdown(f"{icon} **{name}** — Error: {detail}")

            st.rerun()

    st.divider()

    # ── Paste text directly ───────────────────────────────────────────────────
    st.markdown("### 📝 Or paste text directly")
    paste_title = st.text_input("Document title", placeholder="e.g. Remote Work Policy 2024")
    paste_text  = st.text_area("Paste document content here", height=200,
                                placeholder="Paste the full text of your document...")
    paste_cat   = st.selectbox("Category for pasted doc", [
        "HR & People","IT & Security","Sales & Marketing",
        "Finance & Accounting","Legal & Compliance","Operations",
        "Product & Engineering","General",
    ], key="paste_cat")

    if st.button("💾 Save pasted text", use_container_width=True):
        if paste_title and paste_text:
            DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
            safe_name = paste_title.strip().replace(" ", "_") + ".txt"
            dest = DOCUMENTS_PATH / safe_name
            dest.write_text(paste_text, encoding="utf-8")
            entry = ingest_document(dest, category=paste_cat)
            st.success(f"✅ Saved **{safe_name}** — {entry['chunks']} chunks, {entry['words']:,} words")
            st.rerun()
        else:
            st.warning("Please provide both a title and content.")


# ── Document list ─────────────────────────────────────────────────────────────
with col_list:
    st.markdown("### 📚 Current Knowledge Base")
    docs = list_documents()

    if not docs:
        st.info("No documents uploaded yet. Upload your first document to get started.")
    else:
        # Filter by category
        cats = ["All"] + sorted(set(d["category"] for d in docs))
        filter_cat = st.selectbox("Filter by category", cats, key="filter_cat")
        filtered = docs if filter_cat == "All" else [d for d in docs if d["category"] == filter_cat]

        st.markdown(f"<small style='color:#6b7a99'>{len(filtered)} document(s)</small>", unsafe_allow_html=True)
        st.markdown("")

        for doc in sorted(filtered, key=lambda x: x["uploaded"], reverse=True):
            with st.container(border=True):
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    cat_colors = {
                        "HR & People": "🟢",
                        "IT & Security": "🔵",
                        "Sales & Marketing": "🟠",
                        "Finance & Accounting": "🟡",
                        "Legal & Compliance": "🔴",
                        "Operations": "🟣",
                        "Product & Engineering": "⚪",
                        "General": "⬜",
                    }
                    icon = cat_colors.get(doc["category"], "📄")
                    st.markdown(f"**{icon} {doc['filename']}**")
                    st.caption(
                        f"📂 {doc['category']}  ·  "
                        f"🧩 {doc['chunks']} chunks  ·  "
                        f"📝 {doc['words']:,} words  ·  "
                        f"💾 {doc['size_kb']} KB  ·  "
                        f"🕐 {doc['uploaded'][:10]}"
                    )
                with col_del:
                    if st.button("🗑️", key=f"del_{doc['doc_id']}", help=f"Delete {doc['filename']}"):
                        delete_document(doc["doc_id"])
                        st.success(f"Deleted {doc['filename']}")
                        st.rerun()

    st.divider()
    if st.button("🔒 Log out of admin", use_container_width=True):
        st.session_state.admin_authed = False
        st.rerun()
