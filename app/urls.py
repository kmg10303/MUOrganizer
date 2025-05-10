# api/urls.py
from django.urls import path
from .views import generate_mashups 
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('generate-mashups/', generate_mashups),  # or HelloWorldView.as_view()
]
