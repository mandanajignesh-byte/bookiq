"""
Claude API calls:
  - generate_insights(book): summary, genre classification, sentiment
  - rag_answer(question, chunks): contextual answer with source citations
"""
import logging
import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


# ─────────────────────────────────────────────
# AI Insight Generation
# ─────────────────────────────────────────────

def generate_insights(title: str, author: str, description: str, genre: str) -> dict:
    """
    Call Claude to generate:
      1. Summary (2-3 sentences)
      2. Genre classification (single label)
      3. Sentiment analysis (positive / neutral / negative + score 0-1)

    Returns dict: {summary, ai_genre, sentiment, sentiment_score}
    """
    if not description:
        return {
            'summary': '',
            'ai_genre': genre or 'Unknown',
            'sentiment': 'neutral',
            'sentiment_score': 0.5,
        }

    prompt = f"""You are a literary analyst. Analyze this book and respond with ONLY valid JSON, no markdown.

Book: "{title}" by {author}
Genre hint: {genre}
Description: {description[:800]}

Return exactly this JSON structure:
{{
  "summary": "<2-3 sentence summary capturing theme and appeal>",
  "ai_genre": "<single genre label, e.g. Mystery, Romance, Science Fiction, Self-Help, etc.>",
  "sentiment": "<one of: positive, neutral, negative>",
  "sentiment_score": <float 0.0-1.0 where 1.0=very positive>
}}"""

    client = get_client()
    try:
        msg = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=300,
            messages=[{'role': 'user', 'content': prompt}],
        )
        import json
        text = msg.content[0].text.strip()
        # Strip markdown code fences if present
        text = text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)
        return {
            'summary': result.get('summary', ''),
            'ai_genre': result.get('ai_genre', genre or 'Unknown'),
            'sentiment': result.get('sentiment', 'neutral'),
            'sentiment_score': float(result.get('sentiment_score', 0.5)),
        }
    except Exception as e:
        logger.error(f'Claude insights failed for "{title}": {e}')
        return {
            'summary': description[:200] + '...' if len(description) > 200 else description,
            'ai_genre': genre or 'Unknown',
            'sentiment': 'neutral',
            'sentiment_score': 0.5,
        }


# ─────────────────────────────────────────────
# RAG Answer Generation
# ─────────────────────────────────────────────

def rag_answer(question: str, chunks: list[dict], chat_history: list[dict] = None) -> dict:
    """
    Generate a grounded answer from retrieved chunks.

    Args:
        question: User's question.
        chunks: From hybrid_search() — each has 'text', 'title', 'book_id'.
        chat_history: List of {role, content} for multi-turn conversation.

    Returns:
        {answer: str, sources: list[{book_id, title, excerpt}]}
    """
    if not chunks:
        return {
            'answer': "I don't have enough information in the book database to answer that. Try scraping more books first.",
            'sources': [],
        }

    # Build context block with numbered citations
    context_parts = []
    sources = []
    for i, chunk in enumerate(chunks):
        context_parts.append(f'[{i+1}] From "{chunk["title"]}":\n{chunk["text"]}')
        sources.append({
            'book_id': chunk['book_id'],
            'title': chunk['title'],
            'excerpt': chunk['text'][:150] + '...',
            'citation_number': i + 1,
        })

    context = '\n\n'.join(context_parts)

    system_prompt = """You are BookIQ, an intelligent book assistant. Answer questions using ONLY the provided book excerpts.
Always cite your sources using [N] notation matching the numbered excerpts.
If the context doesn't contain enough information, say so clearly.
Be concise, accurate, and helpful."""

    messages = []

    # Include prior conversation turns for multi-turn memory
    if chat_history:
        for turn in chat_history[-6:]:  # last 3 exchanges
            messages.append({'role': turn['role'], 'content': turn['content']})

    messages.append({
        'role': 'user',
        'content': f'Context from book database:\n\n{context}\n\nQuestion: {question}',
    })

    client = get_client()
    try:
        msg = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=600,
            system=system_prompt,
            messages=messages,
        )
        answer = msg.content[0].text.strip()
        return {'answer': answer, 'sources': sources}
    except Exception as e:
        logger.error(f'Claude RAG answer failed: {e}')
        # Graceful degradation: return context directly
        fallback = f'Based on the books in the database:\n\n{chunks[0]["text"][:400]}...'
        return {'answer': fallback, 'sources': sources}
