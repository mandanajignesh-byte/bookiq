import logging
from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache TTL for RAG answers (24 hours)
RAG_CACHE_TTL = 86400


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_book_insights(self, book_id: int):
    """
    Celery task:
    1. Generate Claude insights (summary, genre, sentiment)
    2. Index book chunks into ChromaDB
    Both results are cached to avoid redundant API calls.
    """
    from books.models import Book
    from .claude_client import generate_insights
    from .pipeline import index_book

    try:
        book = Book.objects.get(pk=book_id)

        # Skip if already processed (idempotent)
        if book.ai_insights_generated:
            return f'Book {book_id} already processed.'

        text_for_insights = book.description or book.title

        # Claude insights
        insights = generate_insights(
            title=book.title,
            author=book.author,
            description=book.description,
            genre=book.genre,
        )

        # Index into ChromaDB — use description + title for richer context
        full_text = f'{book.title}. By {book.author}. {book.description}'
        chunk_count = index_book(book.id, book.title, full_text)

        # Save to DB
        book.ai_summary = insights['summary']
        book.ai_genre = insights['ai_genre']
        book.ai_sentiment = insights['sentiment']
        book.ai_sentiment_score = insights['sentiment_score']
        book.ai_insights_generated = True
        book.save(update_fields=[
            'ai_summary', 'ai_genre', 'ai_sentiment',
            'ai_sentiment_score', 'ai_insights_generated',
        ])

        logger.info(f'Insights + {chunk_count} chunks done for book {book_id}: {book.title[:40]}')
        return f'Done: {book.title}'

    except Book.DoesNotExist:
        logger.error(f'Book {book_id} not found.')
    except Exception as exc:
        logger.exception(f'Insights failed for book {book_id}')
        raise self.retry(exc=exc)


@shared_task
def build_all_recommendations():
    """
    Compute cosine similarity between all book-level embeddings.
    Store top-5 neighbours per book in BookRecommendation table.
    """
    import numpy as np
    from books.models import Book, BookRecommendation
    from .pipeline import get_book_embedding

    books = list(Book.objects.filter(ai_insights_generated=True))
    if len(books) < 2:
        return 'Not enough books for recommendations.'

    # Build embedding matrix
    embeddings = []
    valid_books = []
    for book in books:
        full_text = f'{book.title}. By {book.author}. {book.description}'
        emb = get_book_embedding(book.id, full_text)
        if emb:
            embeddings.append(emb)
            valid_books.append(book)

    matrix = np.array(embeddings)  # shape: (N, D)

    # Normalize for cosine similarity
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    matrix_norm = matrix / norms

    # Full similarity matrix
    sim_matrix = matrix_norm @ matrix_norm.T  # (N, N)

    # For each book store top-5 most similar (excluding self)
    to_create = []
    BookRecommendation.objects.all().delete()   # rebuild fresh

    for i, book in enumerate(valid_books):
        sims = sim_matrix[i]
        # Zero out self-similarity
        sims[i] = -1
        top_indices = np.argsort(sims)[::-1][:5]

        for j in top_indices:
            if sims[j] > 0:
                to_create.append(BookRecommendation(
                    source_book=book,
                    recommended_book=valid_books[j],
                    similarity_score=float(sims[j]),
                ))

    BookRecommendation.objects.bulk_create(to_create, ignore_conflicts=True)
    logger.info(f'Rebuilt recommendations: {len(to_create)} pairs across {len(valid_books)} books.')
    return f'Done: {len(to_create)} recommendation pairs'
