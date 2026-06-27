from datetime import datetime, date
from decimal import Decimal
import logging

from django.core.cache import cache
from django.db import connection
from django.db.models import Count
from django.db.models.functions import ExtractYear
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import WeatherData, City
from .serializers import WeatherDataSerializer, CitySerializer
from .weather_service import get_weather_data, normalize_coordinate, is_near_munich
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

logger = logging.getLogger(__name__)

class WeatherAPIView(APIView):
    """
    API Endpoint GET /api/weather/
    Filters:
      - latitude: decimal/float (Required)
      - longitude: decimal/float (Required)
      - date: YYYY-MM-DD (Required if start_date/end_date not provided)
      - start_date: YYYY-MM-DD (Required if date not provided)
      - end_date: YYYY-MM-DD (Required if date not provided)
      - time: HH:MM (Optional)
    
    Implements caching.
    """
    @extend_schema(
        summary="Get historical weather data",
        description="Retrieve weather records for specific coordinates and date range. Quantizes coordinates to 4 decimal places.",
        parameters=[
            OpenApiParameter(name='latitude', description='Latitude of the location (e.g. 48.1351)', required=True, type=OpenApiTypes.DECIMAL),
            OpenApiParameter(name='longitude', description='Longitude of the location (e.g. 11.5820)', required=True, type=OpenApiTypes.DECIMAL),
            OpenApiParameter(name='date', description='Query a single date (YYYY-MM-DD)', required=False, type=OpenApiTypes.DATE),
            OpenApiParameter(name='start_date', description='Start date for range query (YYYY-MM-DD)', required=False, type=OpenApiTypes.DATE),
            OpenApiParameter(name='end_date', description='End date for range query (YYYY-MM-DD)', required=False, type=OpenApiTypes.DATE),
            OpenApiParameter(name='time', description='Specific hour to filter (HH:MM)', required=False, type=OpenApiTypes.STR),
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        latitude_str = request.query_params.get('latitude')
        longitude_str = request.query_params.get('longitude')
        date_str = request.query_params.get('date')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        time_str = request.query_params.get('time')

        # 1. Validation of required parameters
        errors = {}
        if not latitude_str:
            errors['latitude'] = 'This parameter is required.'
        if not longitude_str:
            errors['longitude'] = 'This parameter is required.'
        
        if not date_str and not (start_date_str and end_date_str):
            errors['date_parameters'] = 'You must provide either "date" or both "start_date" and "end_date".'

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Parse and validate coordinates
        # Latitude
        try:
            latitude = normalize_coordinate(latitude_str)
            if not (Decimal('-90.0') <= latitude <= Decimal('90.0')):
                errors['latitude'] = 'Latitude must be between -90 and 90.'
        except ValueError:
            errors['latitude'] = 'Invalid format. Must be a decimal/float.'

        # Longitude
        try:
            longitude = normalize_coordinate(longitude_str)
            if not (Decimal('-180.0') <= longitude <= Decimal('180.0')):
                errors['longitude'] = 'Longitude must be between -180 and 180.'
        except ValueError:
            errors['longitude'] = 'Invalid format. Must be a decimal/float.'

        # Parse Date parameters
        start_date_obj = None
        end_date_obj = None

        if date_str:
            try:
                start_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                end_date_obj = start_date_obj
            except ValueError:
                errors['date'] = 'Invalid format. Must be YYYY-MM-DD.'
        else:
            if start_date_str:
                try:
                    start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                except ValueError:
                    errors['start_date'] = 'Invalid format. Must be YYYY-MM-DD.'
            if end_date_str:
                try:
                    end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    errors['end_date'] = 'Invalid format. Must be YYYY-MM-DD.'

        # Validate Date Range Constraints
        if start_date_obj and end_date_obj:
            today = timezone.localdate()
            min_date = date(1940, 1, 1)  # Open-Meteo historical API start date

            if start_date_obj < min_date:
                errors['start_date'] = 'Historical weather data is only available from 1940-01-01 onwards.'
            if end_date_obj < min_date:
                errors['end_date'] = 'Historical weather data is only available from 1940-01-01 onwards.'
            if start_date_obj > today:
                errors['start_date'] = 'Date cannot be in the future.'
            if end_date_obj > today:
                errors['end_date'] = 'Date cannot be in the future.'

            if not errors:  # Only check range logic if individual bounds are correct
                if start_date_obj > end_date_obj:
                    errors['date_range'] = 'start_date cannot be after end_date.'
                elif (end_date_obj - start_date_obj).days > 366:
                    errors['date_range'] = 'Maximum supported date range is 1 year (366 days) to prevent API rate limits and timeouts.'

        # Time (Optional)
        time_obj = None
        if time_str:
            try:
                time_obj = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                errors['time'] = 'Invalid format. Must be HH:MM.'

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Cache lookup using memory cache
        # Construct key using start_date/end_date representation
        cache_time_suffix = time_str if time_str else "all"
        start_key_str = start_date_obj.strftime("%Y-%m-%d")
        end_key_str = end_date_obj.strftime("%Y-%m-%d")
        cache_key = f"weather_api:{latitude}:{longitude}:{start_key_str}:{end_key_str}:{cache_time_suffix}"
        
        near_munich = is_near_munich(latitude, longitude)
        if near_munich:
            cached_response = cache.get(cache_key)
            if cached_response:
                logger.info(f"Cache HIT for key: {cache_key}")
                return Response(cached_response, status=status.HTTP_200_OK, headers={'X-Cache': 'HIT'})
            logger.info(f"Cache MISS for key: {cache_key}. Querying database/API.")
        else:
            logger.info("Bypassing memory cache check (coordinates > 50km from Munich).")

        # 4. Fetch range using Service Layer
        try:
            weather_records = get_weather_data(latitude, longitude, start_date_obj, end_date_obj, time_obj)
        except RuntimeError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.exception("Unexpected error in WeatherAPIView")
            return Response(
                {"error": "An unexpected server error occurred."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 5. Serialize and Cache the result
        serializer = WeatherDataSerializer(weather_records, many=True)
        response_data = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "start_date": start_key_str,
            "end_date": end_key_str,
            "results": serializer.data
        }

        # Cache for 24 hours (86400 seconds) only if near Munich
        if near_munich:
            cache.set(cache_key, response_data, timeout=86400)
            logger.info(f"Response stored in cache with key: {cache_key}")
            return Response(response_data, status=status.HTTP_200_OK, headers={'X-Cache': 'MISS'})
        
        logger.info("Bypassed memory cache storage (coordinates > 50km from Munich).")
        return Response(response_data, status=status.HTTP_200_OK, headers={'X-Cache': 'BYPASS'})

from rest_framework import viewsets

class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all().order_by('name')
    serializer_class = CitySerializer

from .stats_service import get_weather_statistics

class WeatherStatsAPIView(APIView):
    """
    API Endpoint GET /api/weather/stats/
    Returns database metrics including total entries, unique locations,
    disk storage (PostgreSQL), yearly distribution, and historical temperature extremes.
    Uses raw SQL under the hood for performance and transparency.
    """
    @extend_schema(
        summary="Get database stats",
        description="Returns total records, unique location count, PostgreSQL storage usage, yearly distribution, and warmest/coldest recordings.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        stats = get_weather_statistics()
        return Response(stats, status=status.HTTP_200_OK)

class HealthCheckAPIView(APIView):
    """
    API Endpoint GET /api/health/
    Checks the connection to the database and internal cache.
    """
    @extend_schema(
        summary="Service Health Check",
        description="Performs real-time validation of active connections to the database and memory cache.",
        responses={
            200: OpenApiTypes.OBJECT,
            503: OpenApiTypes.OBJECT
        }
    )
    def get(self, request):
        health_status = {
            "status": "healthy",
            "database": "offline",
            "cache": "offline"
        }
        
        # Check Database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                if cursor.fetchone():
                    health_status["database"] = "online"
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["database_error"] = str(e)
            
        # Check Cache
        try:
            cache.set("health_check_ping", "pong", timeout=5)
            if cache.get("health_check_ping") == "pong":
                health_status["cache"] = "online"
            else:
                health_status["status"] = "unhealthy"
                health_status["cache_error"] = "Could not retrieve value from cache"
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["cache_error"] = str(e)
            
        status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_status, status=status_code)
