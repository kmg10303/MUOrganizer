# api/urls.py
from django.urls import path
from .views import generate_mashups 

urlpatterns = [
    path('generate-mashups/', generate_mashups),  # or HelloWorldView.as_view()
]
