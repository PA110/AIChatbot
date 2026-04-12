"""
RAG Engine — Document ingestion, chunking, embedding, and retrieval.
Uses TF-IDF + cosine similarity as the vector store (no heavy ML deps needed).
Swap embed() for sentence-transformers if you have GPU infrastructure.
"""
import os
import json
import math
import re
import hashlib
import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import Counter

# ── Optional PDF / DOCX support ──────────────────────────────────────────────
try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


VECTOR_STORE_PATH = Path("vector_store")
DOCUMENTS_PATH    = Path("documents")
INDEX_FILE        = VECTOR_STORE_PATH / "index.pkl"
META_FILE         = VECTOR_STORE_PATH / "meta.json"

CHUNK_SIZE    = 400   # words per chunk
CHUNK_OVERLAP = 80    # overlap between chunks
TOP_K         = 5     # how many chunks to retrieve


# ══════════════════════════════════════════════════════════════════════════════
# TEXT EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_text(filepath: Path) -> str:
    suffix = filepath.suffix.lower()

    if suffix == ".txt" or suffix == ".md":
        return filepath.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        if not HAS_PDF:
            return f"[PDF support unavailable — install PyPDF2]"
        text = []
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text.append(t)
        return "\n\n".join(text)

    if suffix in (".docx", ".doc"):
        if not HAS_DOCX:
            return f"[DOCX support unavailable — install python-docx]"
        doc = DocxDocument(filepath)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    return f"[Unsupported file type: {suffix}]"


# ══════════════════════════════════════════════════════════════════════════════
# CHUNKING
# ══════════════════════════════════════════════════════════════════════════════

def chunk_text(text: str, source: str, doc_id: str) -> List[Dict]:
    words = text.split()
    chunks = []
    start  = 0
    idx    = 0

    while start < len(words):
        end  = min(start + CHUNK_SIZE, len(words))
        body = " ".join(words[start:end])
        chunks.append({
            "id":       f"{doc_id}_chunk_{idx}",
            "doc_id":   doc_id,
            "source":   source,
            "chunk_idx": idx,
            "text":     body,
            "word_count": end - start,
        })
        start += CHUNK_SIZE - CHUNK_OVERLAP
        idx   += 1

    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# TF-IDF VECTOR STORE  (lightweight, no external ML libs required)
# ══════════════════════════════════════════════════════════════════════════════

def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    # simple stopword removal
    stops = {"the","a","an","and","or","but","in","on","at","to","for",
             "of","with","by","from","is","are","was","were","be","been",
             "has","have","had","do","does","did","will","would","could",
             "should","may","might","this","that","these","those","it",
             "its","as","not","no","so","if","about","up","out","into"}
    return [t for t in tokens if t not in stops and len(t) > 1]


class TFIDFStore:
    def __init__(self):
        self.chunks:  List[Dict] = []
        self.tf_vecs: List[Dict] = []   # per-chunk TF
        self.idf:     Dict[str, float] = {}
        self.vocab:   set = set()

    def _tf(self, tokens: List[str]) -> Dict[str, float]:
        counts = Counter(tokens)
        total  = max(len(tokens), 1)
        return {t: c / total for t, c in counts.items()}

    def _compute_idf(self):
        N = len(self.chunks)
        df: Dict[str, int] = Counter()
        for vec in self.tf_vecs:
            for term in vec:
                df[term] += 1
        self.idf = {t: math.log((N + 1) / (d + 1)) + 1 for t, d in df.items()}

    def add_chunks(self, new_chunks: List[Dict]):
        for chunk in new_chunks:
            tokens = tokenize(chunk["text"])
            self.vocab.update(tokens)
            self.tf_vecs.append(self._tf(tokens))
            self.chunks.append(chunk)
        self._compute_idf()

    def remove_doc(self, doc_id: str):
        keep = [i for i, c in enumerate(self.chunks) if c["doc_id"] != doc_id]
        self.chunks   = [self.chunks[i]   for i in keep]
        self.tf_vecs  = [self.tf_vecs[i]  for i in keep]
        self._compute_idf()

    def _tfidf_vec(self, tf: Dict[str, float]) -> Dict[str, float]:
        return {t: tf[t] * self.idf.get(t, 0) for t in tf}

    def _cosine(self, a: Dict, b: Dict) -> float:
        common = set(a) & set(b)
        if not common:
            return 0.0
        dot  = sum(a[t] * b[t] for t in common)
        norm_a = math.sqrt(sum(v*v for v in a.values()))
        norm_b = math.sqrt(sum(v*v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, top_k: int = TOP_K) -> List[Tuple[Dict, float]]:
        q_tokens = tokenize(query)
        q_tf     = self._tf(q_tokens)
        q_tfidf  = self._tfidf_vec(q_tf)

        scores = []
        for i, chunk_tf in enumerate(self.tf_vecs):
            chunk_tfidf = self._tfidf_vec(chunk_tf)
            score = self._cosine(q_tfidf, chunk_tfidf)
            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [(self.chunks[i], s) for i, s in scores[:top_k] if s > 0]

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: Path) -> "TFIDFStore":
        if not path.exists():
            return TFIDFStore()
        with open(path, "rb") as f:
            return pickle.load(f)


# ══════════════════════════════════════════════════════════════════════════════
# METADATA STORE
# ══════════════════════════════════════════════════════════════════════════════

def load_meta() -> Dict:
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not META_FILE.exists():
        return {"documents": {}}
    with open(META_FILE) as f:
        return json.load(f)


def save_meta(meta: Dict):
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def ingest_document(filepath: Path, category: str = "General") -> Dict:
    """Extract, chunk, and index a document. Returns metadata entry."""
    store = TFIDFStore.load(INDEX_FILE)
    meta  = load_meta()

    doc_id   = hashlib.md5(filepath.name.encode()).hexdigest()[:12]
    filename = filepath.name

    # Remove existing version if re-uploading
    if doc_id in meta["documents"]:
        store.remove_doc(doc_id)

    text   = extract_text(filepath)
    chunks = chunk_text(text, filename, doc_id)
    store.add_chunks(chunks)
    store.save(INDEX_FILE)

    entry = {
        "doc_id":    doc_id,
        "filename":  filename,
        "category":  category,
        "chunks":    len(chunks),
        "words":     len(text.split()),
        "uploaded":  datetime.now().isoformat(timespec="seconds"),
        "size_kb":   round(filepath.stat().st_size / 1024, 1),
    }
    meta["documents"][doc_id] = entry
    save_meta(meta)
    return entry


def delete_document(doc_id: str) -> bool:
    store = TFIDFStore.load(INDEX_FILE)
    meta  = load_meta()
    if doc_id not in meta["documents"]:
        return False
    store.remove_doc(doc_id)
    store.save(INDEX_FILE)
    del meta["documents"][doc_id]
    save_meta(meta)
    return True


def retrieve(query: str, top_k: int = TOP_K) -> List[Dict]:
    """Return top-k relevant chunks for a query."""
    store = TFIDFStore.load(INDEX_FILE)
    results = store.search(query, top_k=top_k)
    out = []
    for chunk, score in results:
        out.append({**chunk, "score": round(score, 4)})
    return out


def list_documents() -> List[Dict]:
    return list(load_meta()["documents"].values())


def get_stats() -> Dict:
    meta   = load_meta()
    docs   = meta["documents"]
    store  = TFIDFStore.load(INDEX_FILE)
    cats   = Counter(d["category"] for d in docs.values())
    return {
        "total_documents": len(docs),
        "total_chunks":    len(store.chunks),
        "total_words":     sum(d["words"] for d in docs.values()),
        "categories":      dict(cats),
    }
