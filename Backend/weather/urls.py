from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WeatherAPIView, CityViewSet, WeatherStatsAPIView, HealthCheckAPIView

router = DefaultRouter()
router.register(r'cities', CityViewSet, basename='city')

urlpatterns = [
    path('health/', HealthCheckAPIView.as_view(), name='health_check_api'),
    path('weather/stats/', WeatherStatsAPIView.as_view(), name='weather_stats_api'),
    path('weather/', WeatherAPIView.as_view(), name='weather_api'),
    path('', include(router.urls)),
]
