from django.urls import path
from . import views

urlpatterns = [
  path('', views.index),
  path('signin', views.index),
  path('accounts/profile/', views.index),
]
