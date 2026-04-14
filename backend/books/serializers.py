from rest_framework import serializers
from .models import Book, BookRecommendation, ChatHistory


class BookListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list/dashboard view."""
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'rating', 'review_count',
            'genre', 'ai_genre', 'price', 'book_url', 'cover_image_url',
            'ai_insights_generated', 'created_at',
        ]


class BookDetailSerializer(serializers.ModelSerializer):
    """Full serializer including AI insights."""
    recommendations = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = '__all__'

    def get_recommendations(self, obj):
        recs = BookRecommendation.objects.filter(source_book=obj).select_related('recommended_book')[:5]
        return [
            {
                'id': r.recommended_book.id,
                'title': r.recommended_book.title,
                'author': r.recommended_book.author,
                'cover_image_url': r.recommended_book.cover_image_url,
                'similarity_score': round(r.similarity_score, 3),
            }
            for r in recs
        ]


class ChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = ['id', 'session_id', 'question', 'answer', 'sources', 'book', 'created_at']
