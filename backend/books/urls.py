from django.urls import path
from . import views

urlpatterns = [
    path('', views.BookListView.as_view(), name='book-list'),
    path('upload/', views.upload_book, name='book-upload'),
    path('genres/', views.genre_list, name='genre-list'),
    path('history/<str:session_id>/', views.chat_history, name='chat-history'),
    path('<int:pk>/', views.BookDetailView.as_view(), name='book-detail'),
    path('<int:pk>/recommendations/', views.book_recommendations, name='book-recommendations'),
]
