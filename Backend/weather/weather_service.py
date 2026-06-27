from datetime import datetime, time, timezone
from decimal import Decimal
import requests
import logging
from django.db.models import Q
from .models import WeatherData

logger = logging.getLogger(__name__)

def normalize_coordinate(val) -> Decimal:
    """
    Normalizes a coordinate to 4 decimal places for consistent storage and lookup.
    4 decimal places gives a precision of ~11 meters, which is perfect for weather data.
    """
    try:
        return Decimal(str(val)).quantize(Decimal('0.0001'))
    except Exception as e:
        raise ValueError(f"Invalid coordinate format: {val}") from e

import math

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points on the Earth's surface
    using the Haversine formula.
    """
    R = 6371.0  # Earth's radius in kilometers

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def is_near_munich(lat: Decimal, lon: Decimal) -> bool:
    """
    Checks if the coordinates are within 50 km of Munich city center (48.135, 11.582).
    """
    distance = calculate_distance_km(float(lat), float(lon), 48.135, 11.582)
    return distance <= 50.0


def get_weather_data(latitude: Decimal, longitude: Decimal, start_date, end_date, time_obj=None):
    """
    Retrieves weather data for the given coordinates and date range (inclusive).
    
    1. Checks if the requested weather data already exists in PostgreSQL database.
    2. If all data is found (either all hourly records for the range, or the specific
       hour records for each day of the range), returns the records.
    3. If not, fetches the range from the Open-Meteo Historical Weather API in one single request.
    4. Saves newly fetched data to PostgreSQL database in bulk.
    5. Returns the requested records.
    """
    # Normalize coordinates
    lat_norm = normalize_coordinate(latitude)
    lon_norm = normalize_coordinate(longitude)

    near_munich = is_near_munich(lat_norm, lon_norm)
    logger.info(f"Querying weather for Lat: {lat_norm}, Lon: {lon_norm}, Range: {start_date} to {end_date}. Near Munich (50km): {near_munich}")

    # If near Munich, check database cache first
    db_records = None
    if near_munich:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        days = (end_date - start_date).days + 1
        expected_hours = days * 24

        db_records = WeatherData.objects.filter(
            latitude=lat_norm,
            longitude=lon_norm,
            timestamp__range=(start_dt, end_dt)
        ).order_by('timestamp')

        if time_obj:
            specific_records = db_records.filter(
                timestamp__hour=time_obj.hour,
                timestamp__minute=time_obj.minute
            )
            if specific_records.count() >= days:
                logger.info("DATABASE HIT: Serving range query for specific hour from PostgreSQL cache.")
                return list(specific_records)
        else:
            if db_records.count() >= expected_hours:
                logger.info("DATABASE HIT: Serving full range query from PostgreSQL cache.")
                return list(db_records)

    # Cache miss or bypassed: Query Open-Meteo API
    if near_munich:
        logger.info("DATABASE MISS / API HIT: Fetching range from Open-Meteo API to cache in database.")
    else:
        logger.info("API HIT (Proxy Mode): Fetching range from Open-Meteo API directly (bypassing DB).")
    api_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": float(lat_norm),
        "longitude": float(lon_norm),
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "hourly": "temperature_2m",
    }

    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "hourly" not in data or "time" not in data["hourly"] or "temperature_2m" not in data["hourly"]:
            raise ValueError("Invalid JSON response from Open-Meteo API.")

        hourly_times = data["hourly"]["time"]
        hourly_temps = data["hourly"]["temperature_2m"]

        weather_objects = []
        for t_str, temp in zip(hourly_times, hourly_temps):
            if temp is None:
                continue
            dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
            weather_objects.append(
                WeatherData(
                    latitude=lat_norm,
                    longitude=lon_norm,
                    timestamp=dt,
                    temperature=temp
                )
            )

        if weather_objects:
            if near_munich:
                WeatherData.objects.bulk_create(weather_objects, ignore_conflicts=True)
                logger.info(f"Successfully cached {len(weather_objects)} hourly records to database.")
            else:
                logger.info("Bypassed database caching (coordinates > 50km from Munich).")
                # Filter locally in memory for proxy mode if time is specified
                if time_obj:
                    return [
                        obj for obj in weather_objects
                        if obj.timestamp.hour == time_obj.hour and obj.timestamp.minute == time_obj.minute
                    ]
                return weather_objects

        if near_munich:
            # Re-fetch from DB to get consistent queryset
            db_records = WeatherData.objects.filter(
                latitude=lat_norm,
                longitude=lon_norm,
                timestamp__range=(start_dt, end_dt)
            ).order_by('timestamp')

            if time_obj:
                return list(db_records.filter(
                    timestamp__hour=time_obj.hour,
                    timestamp__minute=time_obj.minute
                ))
            return list(db_records)
        else:
            return []

    except requests.RequestException as e:
        logger.error(f"HTTP request to Open-Meteo failed: {e}")
        if near_munich and db_records and db_records.exists():
            logger.warning("HTTP failed. Returning partial/existing database records as fallback.")
            if time_obj:
                return list(db_records.filter(
                    timestamp__hour=time_obj.hour,
                    timestamp__minute=time_obj.minute
                ))
            return list(db_records)
        raise RuntimeError("Weather API is currently unavailable and no cached data exists.") from e
    except Exception as e:
        logger.error(f"Error processing weather data: {e}")
        raise

