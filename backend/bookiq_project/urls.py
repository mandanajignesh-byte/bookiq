from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/books/', include('books.urls')),
    path('api/rag/', include('rag.urls')),
    path('api/scraper/', include('scraper_app.urls')),
]
