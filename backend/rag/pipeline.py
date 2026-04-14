"""
RAG pipeline core:
  - Semantic chunking (sentence-aware, ~300 tokens with 50-token overlap)
  - Embedding via sentence-transformers all-MiniLM-L6-v2 (local, free)
  - ChromaDB for vector storage
  - BM25 for keyword search
  - Reciprocal Rank Fusion (RRF) to merge both result sets → hybrid search
"""
import re
import logging
import hashlib
from typing import Optional
from functools import lru_cache

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from django.conf import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 300        # target tokens per chunk
CHUNK_OVERLAP = 50      # overlap tokens between adjacent chunks
TOP_K = 8               # candidates from each retriever before fusion
FINAL_K = 5             # chunks returned to LLM after fusion


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load model once and cache in memory for the process lifetime."""
    logger.info(f'Loading embedding model: {settings.EMBEDDING_MODEL}')
    return SentenceTransformer(settings.EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.Client:
    return chromadb.PersistentClient(
        path=settings.CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False),
    )


def get_collection() -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name='book_chunks',
        metadata={'hnsw:space': 'cosine'},
    )


# ─────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Naive whitespace tokenizer — fast enough for chunking purposes."""
    return text.split()


def semantic_chunk(text: str, book_id: int, title: str) -> list[dict]:
    """
    Split text into semantically coherent chunks:
    1. Split on sentence boundaries first.
    2. Greedily accumulate sentences until CHUNK_SIZE tokens are reached.
    3. Overlap: carry the last CHUNK_OVERLAP tokens into the next chunk.

    Returns list of dicts: {chunk_id, text, book_id, title, chunk_index}
    """
    if not text or not text.strip():
        return []

    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_tokens: list[str] = []
    chunk_index = 0

    for sentence in sentences:
        sentence_tokens = _tokenize(sentence)

        if len(current_tokens) + len(sentence_tokens) > CHUNK_SIZE and current_tokens:
            # Emit current chunk
            chunk_text = ' '.join(current_tokens)
            chunk_id = hashlib.md5(f'{book_id}_{chunk_index}_{chunk_text[:50]}'.encode()).hexdigest()
            chunks.append({
                'chunk_id': chunk_id,
                'text': chunk_text,
                'book_id': book_id,
                'title': title,
                'chunk_index': chunk_index,
            })
            chunk_index += 1
            # Overlap: keep last CHUNK_OVERLAP tokens
            current_tokens = current_tokens[-CHUNK_OVERLAP:] + sentence_tokens
        else:
            current_tokens.extend(sentence_tokens)

    # Emit final chunk
    if current_tokens:
        chunk_text = ' '.join(current_tokens)
        chunk_id = hashlib.md5(f'{book_id}_{chunk_index}_{chunk_text[:50]}'.encode()).hexdigest()
        chunks.append({
            'chunk_id': chunk_id,
            'text': chunk_text,
            'book_id': book_id,
            'title': title,
            'chunk_index': chunk_index,
        })

    return chunks


# ─────────────────────────────────────────────
# Indexing
# ─────────────────────────────────────────────

def index_book(book_id: int, title: str, text: str) -> int:
    """
    Chunk + embed a book's text and upsert into ChromaDB.
    Returns number of chunks stored.
    """
    if not text:
        return 0

    chunks = semantic_chunk(text, book_id, title)
    if not chunks:
        return 0

    model = get_embedding_model()
    collection = get_collection()

    texts = [c['text'] for c in chunks]
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False).tolist()

    collection.upsert(
        ids=[c['chunk_id'] for c in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {'book_id': c['book_id'], 'title': c['title'], 'chunk_index': c['chunk_index']}
            for c in chunks
        ],
    )

    logger.info(f'Indexed {len(chunks)} chunks for book {book_id} ({title[:40]})')
    return len(chunks)


def delete_book_chunks(book_id: int):
    """Remove all chunks for a book (call before re-indexing)."""
    collection = get_collection()
    results = collection.get(where={'book_id': book_id})
    if results['ids']:
        collection.delete(ids=results['ids'])


# ─────────────────────────────────────────────
# Retrieval — Hybrid BM25 + Vector with RRF
# ─────────────────────────────────────────────

def _reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion.
    Score = Σ 1/(k + rank_i) across retrievers.
    Higher is better.
    """
    scores: dict[str, float] = {}
    all_docs: dict[str, dict] = {}

    for rank, doc in enumerate(vector_results):
        cid = doc['chunk_id']
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
        all_docs[cid] = doc

    for rank, doc in enumerate(bm25_results):
        cid = doc['chunk_id']
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
        all_docs[cid] = doc

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [dict(all_docs[cid], rrf_score=scores[cid]) for cid in sorted_ids]


def hybrid_search(query: str, top_k: int = FINAL_K, book_id: Optional[int] = None) -> list[dict]:
    """
    Hybrid search: combine dense vector retrieval + BM25 sparse retrieval via RRF.

    Args:
        query: User question string.
        top_k: Number of chunks to return.
        book_id: If set, restrict search to a single book.

    Returns:
        List of chunk dicts with keys: chunk_id, text, book_id, title, rrf_score
    """
    collection = get_collection()
    model = get_embedding_model()

    where_filter = {'book_id': book_id} if book_id else None

    # ── Dense retrieval ──────────────────────────────
    query_embedding = model.encode([query])[0].tolist()
    vector_raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(TOP_K, collection.count() or 1),
        where=where_filter,
        include=['documents', 'metadatas', 'distances'],
    )

    vector_results = []
    if vector_raw['ids'] and vector_raw['ids'][0]:
        for cid, doc, meta, dist in zip(
            vector_raw['ids'][0],
            vector_raw['documents'][0],
            vector_raw['metadatas'][0],
            vector_raw['distances'][0],
        ):
            vector_results.append({
                'chunk_id': cid, 'text': doc,
                'book_id': meta.get('book_id'),
                'title': meta.get('title', ''),
                'vector_score': 1 - dist,  # cosine: distance → similarity
            })

    # ── BM25 sparse retrieval ────────────────────────
    # Fetch all relevant documents for BM25 corpus
    all_raw = collection.get(where=where_filter, include=['documents', 'metadatas'])
    bm25_results = []
    if all_raw['ids']:
        corpus_tokens = [_tokenize(doc.lower()) for doc in all_raw['documents']]
        bm25 = BM25Okapi(corpus_tokens)
        query_tokens = _tokenize(query.lower())
        bm25_scores = bm25.get_scores(query_tokens)

        # Get top-K by BM25
        ranked_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:TOP_K]
        for idx in ranked_indices:
            meta = all_raw['metadatas'][idx]
            bm25_results.append({
                'chunk_id': all_raw['ids'][idx],
                'text': all_raw['documents'][idx],
                'book_id': meta.get('book_id'),
                'title': meta.get('title', ''),
                'bm25_score': float(bm25_scores[idx]),
            })

    # ── Reciprocal Rank Fusion ────────────────────────
    fused = _reciprocal_rank_fusion(vector_results, bm25_results)
    return fused[:top_k]


# ─────────────────────────────────────────────
# Book-level embedding for recommendations
# ─────────────────────────────────────────────

def get_book_embedding(book_id: int, text: str) -> list[float]:
    """
    Mean-pool all chunk embeddings for a book → single book-level vector.
    Used for recommendation cosine similarity.
    """
    model = get_embedding_model()
    collection = get_collection()

    results = collection.get(where={'book_id': book_id}, include=['embeddings'])
    if results['embeddings']:
        import numpy as np
        embeddings = np.array(results['embeddings'])
        mean_emb = embeddings.mean(axis=0)
        return mean_emb.tolist()

    # Fallback: encode the raw text directly
    return model.encode([text[:1000]])[0].tolist()
