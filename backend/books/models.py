from django.db import models


class Book(models.Model):
    """Core book metadata scraped from the web."""

    title = models.CharField(max_length=500)
    author = models.CharField(max_length=300, blank=True, default='Unknown')
    rating = models.FloatField(null=True, blank=True)          # 1-5 stars
    review_count = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    genre = models.CharField(max_length=100, blank=True)       # from scrape taxonomy
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    availability = models.CharField(max_length=100, blank=True)
    book_url = models.URLField(max_length=255, unique=True)
    cover_image_url = models.URLField(max_length=500, blank=True)
    upc = models.CharField(max_length=50, blank=True)

    # AI-generated fields (populated async after scraping)
    ai_summary = models.TextField(blank=True)
    ai_genre = models.CharField(max_length=100, blank=True)    # Claude-classified genre
    ai_sentiment = models.CharField(max_length=50, blank=True) # positive / neutral / negative
    ai_sentiment_score = models.FloatField(null=True, blank=True)
    ai_insights_generated = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['genre']),
            models.Index(fields=['rating']),
            models.Index(fields=['ai_genre']),
        ]

    def __str__(self):
        return f"{self.title} ({self.author})"


class BookRecommendation(models.Model):
    """
    Precomputed 'if you like X → try Y' pairs via embedding cosine similarity.
    Stored so we don't recompute on every request.
    """
    source_book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='recommendations')
    recommended_book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='recommended_by')
    similarity_score = models.FloatField()

    class Meta:
        ordering = ['-similarity_score']
        unique_together = ('source_book', 'recommended_book')


class ChatHistory(models.Model):
    """Persist Q&A conversations so users can revisit past queries."""
    session_id = models.CharField(max_length=100, db_index=True)
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list)   # list of {book_id, title, chunk}
    book = models.ForeignKey(Book, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
