"""
Celery async tasks:
  - run_scrape_task: scrape catalogue + save books + trigger AI insights
  - generate_book_insights_task: Claude API → summary, genre, sentiment
  - build_recommendations_task: cosine similarity across all embeddings
"""
import json
import logging
import hashlib
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _send_ws_progress(job_id: str, current: int, total: int, message: str, status: str = 'running'):
    """Push progress update to WebSocket group for this scrape job."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'scrape_{job_id}',
        {
            'type': 'scrape_progress',
            'current': current,
            'total': total,
            'message': message,
            'status': status,
            'percent': round((current / max(total, 1)) * 100),
        }
    )


@shared_task(bind=True)
def run_scrape_task(self, job_id: str, max_books: int = 50):
    """
    Full scrape pipeline:
    1. Scrape books.toscrape.com (+ Open Library enrichment)
    2. Upsert into MySQL
    3. Trigger async AI insight generation per book
    4. Trigger recommendation rebuild
    """
    from books.models import Book
    from .scraper import scrape_catalogue
    from rag.tasks import generate_book_insights, build_all_recommendations

    def progress(current, total, message):
        _send_ws_progress(job_id, current, total, message)

    try:
        _send_ws_progress(job_id, 0, 1, 'Starting scrape...', 'running')
        books_data = scrape_catalogue(max_books=max_books, progress_callback=progress)

        _send_ws_progress(job_id, 0, len(books_data), 'Saving to database...', 'saving')

        saved_ids = []
        for i, data in enumerate(books_data):
            book, created = Book.objects.update_or_create(
                book_url=data['book_url'],
                defaults={k: v for k, v in data.items() if k != 'book_url'}
            )
            saved_ids.append(book.id)
            _send_ws_progress(job_id, i + 1, len(books_data),
                               f'Saved: {book.title[:40]}', 'saving')

        # Kick off AI insight generation for each book (async)
        for book_id in saved_ids:
            generate_book_insights.delay(book_id)

        # Rebuild all embedding-based recommendations once insights are done
        build_all_recommendations.apply_async(countdown=30)  # 30s head start for insights

        _send_ws_progress(job_id, len(books_data), len(books_data),
                          f'Done! {len(saved_ids)} books saved. AI insights generating...', 'done')

    except Exception as exc:
        logger.exception(f'Scrape job {job_id} failed')
        _send_ws_progress(job_id, 0, 1, f'Error: {str(exc)}', 'error')
        raise
