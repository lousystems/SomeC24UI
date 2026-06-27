from django.db import models

class WeatherData(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField()
    temperature = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['latitude', 'longitude', 'timestamp'],
                name='unique_lat_lon_timestamp'
            )
        ]
        indexes = [
            models.Index(fields=['latitude', 'longitude', 'timestamp']),
        ]

    def __str__(self):
        return f"Lat: {self.latitude}, Lon: {self.longitude} at {self.timestamp} - Temp: {self.temperature}°C"

class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        verbose_name_plural = "Cities"
        indexes = [
            models.Index(fields=['name']),
        ]

    def save(self, *args, **kwargs):
        # Normalize coordinates before saving to database
        from .weather_service import normalize_coordinate
        self.latitude = normalize_coordinate(self.latitude)
        self.longitude = normalize_coordinate(self.longitude)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"
