from decimal import Decimal
from datetime import datetime, timezone
import requests

from django.core.management.base import BaseCommand
from weather.models import WeatherData
from weather.weather_service import normalize_coordinate

class Command(BaseCommand):
    help = 'Pre-populates the database with noon (12:00) temperatures for Munich in 1980'

    def handle(self, *args, **options):
        # Target coordinates: Munich (around Lat 48.1351, Lon 11.582)
        lat = normalize_coordinate(Decimal('48.1351'))
        lon = normalize_coordinate(Decimal('11.582'))
        
        self.stdout.write(f"Fetching 1980 historical weather for Munich (Lat: {lat}, Lon: {lon})...")
        
        api_url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": float(lat),
            "longitude": float(lon),
            "start_date": "1980-01-01",
            "end_date": "1980-12-31",
            "hourly": "temperature_2m"
        }
        
        try:
            response = requests.get(api_url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if "hourly" not in data or "time" not in data["hourly"] or "temperature_2m" not in data["hourly"]:
                self.stderr.write("Invalid response format from Open-Meteo API.")
                return

            hourly_times = data["hourly"]["time"]
            hourly_temps = data["hourly"]["temperature_2m"]
            
            weather_objects = []
            for t_str, temp in zip(hourly_times, hourly_temps):
                if temp is None:
                    continue
                
                # Check if the time is 12:00 (noon)
                # Open-Meteo returns times in ISO format like '1980-01-01T12:00'
                if t_str.endswith("T12:00"):
                    dt = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                    weather_objects.append(
                        WeatherData(
                            latitude=lat,
                            longitude=lon,
                            timestamp=dt,
                            temperature=temp
                        )
                    )
            
            if weather_objects:
                # bulk_create ignores duplicate rows if command is run multiple times
                WeatherData.objects.bulk_create(weather_objects, ignore_conflicts=True)
                
                # Count current total to verify
                count = WeatherData.objects.filter(
                    latitude=lat,
                    longitude=lon,
                    timestamp__year=1980
                ).count()
                
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully fetched and processed 1980 noon temperatures. Total records in DB: {count}."
                ))
            else:
                self.stdout.write(self.style.WARNING("No noon temperatures found to cache."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error fetching data: {str(e)}"))
