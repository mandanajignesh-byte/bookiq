import hashlib
import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from books.models import ChatHistory

logger = logging.getLogger(__name__)

RAG_CACHE_TTL = 86400  # 24 hours


@api_view(['POST'])
def ask_question(request):
    """
    POST /api/rag/ask/
    Body: {
        "question": "What are some good mystery books?",
        "session_id": "abc123",          # for chat history
        "book_id": 42 (optional)         # restrict search to one book
    }

    Pipeline:
    1. Check Redis cache (hash of question + book_id)
    2. Hybrid search (BM25 + vector + RRF)
    3. Claude RAG answer generation
    4. Cache result + persist to ChatHistory
    """
    from .pipeline import hybrid_search
    from .claude_client import rag_answer

    question = request.data.get('question', '').strip()
    session_id = request.data.get('session_id', 'default')
    book_id = request.data.get('book_id')  # optional

    if not question:
        return Response({'error': 'question is required'}, status=status.HTTP_400_BAD_REQUEST)

    # ── Cache lookup ──────────────────────────────────
    cache_key = 'rag:' + hashlib.md5(f'{question}:{book_id}'.encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached:
        logger.info(f'Cache hit for question: {question[:60]}')
        return Response({**cached, 'cached': True})

    # ── Retrieve prior conversation for multi-turn context ──
    prior = ChatHistory.objects.filter(session_id=session_id).order_by('-created_at')[:3]
    chat_history = []
    for h in reversed(prior):
        chat_history.append({'role': 'user', 'content': h.question})
        chat_history.append({'role': 'assistant', 'content': h.answer})

    # ── Hybrid retrieval ──────────────────────────────
    chunks = hybrid_search(question, top_k=5, book_id=int(book_id) if book_id else None)

    # ── Claude answer ─────────────────────────────────
    result = rag_answer(question, chunks, chat_history=chat_history)

    # ── Persist + cache ───────────────────────────────
    ChatHistory.objects.create(
        session_id=session_id,
        question=question,
        answer=result['answer'],
        sources=result['sources'],
        book_id=book_id if book_id else None,
    )
    cache.set(cache_key, result, RAG_CACHE_TTL)

    return Response({**result, 'cached': False})
