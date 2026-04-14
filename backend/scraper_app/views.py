import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .tasks import run_scrape_task


@api_view(['POST'])
def start_scrape(request):
    """
    POST /api/scraper/start/
    Body: { "max_books": 50 }
    Kicks off async Celery scrape job. Returns job_id for WS progress tracking.
    """
    max_books = int(request.data.get('max_books', 50))
    max_books = min(max_books, 200)  # hard cap

    job_id = str(uuid.uuid4())
    run_scrape_task.delay(job_id=job_id, max_books=max_books)

    return Response({'job_id': job_id, 'status': 'started', 'max_books': max_books})


@api_view(['GET'])
def scrape_status(request, job_id):
    """GET /api/scraper/status/<job_id>/ — simple check (WS preferred for live updates)."""
    return Response({'job_id': job_id, 'message': 'Use WebSocket for live progress.'})
