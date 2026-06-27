from rest_framework import serializers
from .models import WeatherData, City
from .weather_service import normalize_coordinate

class WeatherDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherData
        fields = ['latitude', 'longitude', 'timestamp', 'temperature']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'latitude', 'longitude']

    def validate_latitude(self, value):
        if not (-90.0 <= float(value) <= 90.0):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return normalize_coordinate(value)

    def validate_longitude(self, value):
        if not (-180.0 <= float(value) <= 180.0):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return normalize_coordinate(value)
