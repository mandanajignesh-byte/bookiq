from rest_framework import generics, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from .models import Book, ChatHistory
from .serializers import BookListSerializer, BookDetailSerializer, ChatHistorySerializer


class BookListView(generics.ListAPIView):
    """
    GET /api/books/
    List all books with optional search, genre filter, and ordering.
    Query params: ?search=<term>&genre=<genre>&ordering=rating,-created_at
    """
    serializer_class = BookListSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['rating', 'title', 'created_at', 'price']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Book.objects.all()
        search = self.request.query_params.get('search')
        genre = self.request.query_params.get('genre')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(author__icontains=search))
        if genre:
            qs = qs.filter(Q(genre__iexact=genre) | Q(ai_genre__iexact=genre))
        return qs


class BookDetailView(generics.RetrieveAPIView):
    """
    GET /api/books/<id>/
    Full book details including AI insights and precomputed recommendations.
    """
    queryset = Book.objects.all()
    serializer_class = BookDetailSerializer


@api_view(['GET'])
def book_recommendations(request, pk):
    """
    GET /api/books/<id>/recommendations/
    Returns top-5 similar books by embedding cosine similarity.
    """
    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist:
        return Response({'error': 'Book not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = BookDetailSerializer(book, context={'request': request})
    return Response(serializer.data['recommendations'])


@api_view(['GET'])
def genre_list(request):
    """GET /api/books/genres/ — distinct genre values for filter dropdowns."""
    genres = (
        Book.objects.exclude(ai_genre='')
        .values_list('ai_genre', flat=True)
        .distinct()
        .order_by('ai_genre')
    )
    return Response(list(genres))


@api_view(['GET'])
def chat_history(request, session_id):
    """GET /api/books/history/<session_id>/ — fetch past Q&A for a session."""
    history = ChatHistory.objects.filter(session_id=session_id)[:50]
    return Response(ChatHistorySerializer(history, many=True).data)


@api_view(['POST'])
def upload_book(request):
    """
    POST /api/books/upload/
    Manually add a book and trigger AI insight generation.
    Body: { title, author, description, book_url, ... }
    """
    serializer = BookDetailSerializer(data=request.data)
    if serializer.is_valid():
        book = serializer.save()
        # Trigger async AI insight generation
        from rag.tasks import generate_book_insights
        generate_book_insights.delay(book.id)
        return Response(BookDetailSerializer(book).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
