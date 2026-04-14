from django.urls import path
from . import views

urlpatterns = [
    path('start/', views.start_scrape, name='scrape-start'),
    path('status/<str:job_id>/', views.scrape_status, name='scrape-status'),
]
