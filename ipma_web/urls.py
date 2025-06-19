from django.urls import path
from .views import ForecastAPIView

urlpatterns = [
    path("api/forecast/", ForecastAPIView.as_view(), name="forecast"),
]
