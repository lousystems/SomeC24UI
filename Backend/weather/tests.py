from datetime import datetime, date, time, timezone
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import WeatherData, City
from .weather_service import is_near_munich, normalize_coordinate

class WeatherTests(APITestCase):

    def setUp(self):
        # Clear cache before each test run
        cache.clear()
        # Clean any DB entries that might persist
        WeatherData.objects.all().delete()
        City.objects.all().delete()

    def test_coordinate_normalization(self):
        self.assertEqual(normalize_coordinate('48.1351'), Decimal('48.1351'))
        self.assertEqual(normalize_coordinate('11.582'), Decimal('11.5820'))
        self.assertEqual(normalize_coordinate(11.5820001), Decimal('11.5820'))
        with self.assertRaises(ValueError):
            normalize_coordinate('not-a-number')

    def test_is_near_munich(self):
        # Coordinates inside Munich
        self.assertTrue(is_near_munich(Decimal('48.1351'), Decimal('11.5820')))
        # Coordinates within 50 km (e.g. Dachau ~18km)
        self.assertTrue(is_near_munich(Decimal('48.2600'), Decimal('11.4300')))
        # Coordinates outside 50 km (Berlin ~500km)
        self.assertFalse(is_near_munich(Decimal('52.5200'), Decimal('13.4050')))

    @patch('requests.get')
    def test_api_fetch_and_cache_single_date(self, mock_get):
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "latitude": 48.1351,
            "longitude": 11.582,
            "hourly": {
                "time": [f"1980-01-01T{i:02d}:00" for i in range(24)],
                "temperature_2m": [1.5 + i for i in range(24)]
            }
        }

        url = reverse('weather_api')
        params = {
            'latitude': '48.1351',
            'longitude': '11.582',
            'date': '1980-01-01'
        }

        # First Request: Cache MISS
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('X-Cache'), 'MISS')
        self.assertEqual(len(response.data['results']), 24)

        # Database should now have all 24 records
        db_count = WeatherData.objects.filter(
            latitude=Decimal('48.1351'),
            longitude=Decimal('11.5820'),
            timestamp__year=1980
        ).count()
        self.assertEqual(db_count, 24)

        # Second Request: Cache HIT
        response_cached = self.client.get(url, params)
        self.assertEqual(response_cached.status_code, status.HTTP_200_OK)
        self.assertEqual(response_cached.headers.get('X-Cache'), 'HIT')

    @patch('requests.get')
    def test_api_fetch_and_cache_date_range(self, mock_get):
        # Mock range response for 2 days (48 hours)
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        times = [f"1980-01-01T{i:02d}:00" for i in range(24)] + [f"1980-01-02T{i:02d}:00" for i in range(24)]
        temps = [1.0 + float(i) for i in range(48)]
        
        mock_response.json.return_value = {
            "latitude": 48.1351,
            "longitude": 11.582,
            "hourly": {
                "time": times,
                "temperature_2m": temps
            }
        }

        url = reverse('weather_api')
        params = {
            'latitude': '48.1351',
            'longitude': '11.582',
            'start_date': '1980-01-01',
            'end_date': '1980-01-02'
        }

        # First Request: Cache MISS
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('X-Cache'), 'MISS')
        self.assertEqual(len(response.data['results']), 48)

        # DB Count checks
        db_count = WeatherData.objects.filter(
            latitude=Decimal('48.1351'),
            longitude=Decimal('11.5820')
        ).count()
        self.assertEqual(db_count, 48)

        # Second Request: Cache HIT
        response_cached = self.client.get(url, params)
        self.assertEqual(response_cached.status_code, status.HTTP_200_OK)
        self.assertEqual(response_cached.headers.get('X-Cache'), 'HIT')

    @patch('requests.get')
    def test_api_range_with_specific_time(self, mock_get):
        # Mock range response for 2 days (48 hours)
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        times = [f"1980-01-01T{i:02d}:00" for i in range(24)] + [f"1980-01-02T{i:02d}:00" for i in range(24)]
        temps = [1.0 + float(i) for i in range(48)]
        
        mock_response.json.return_value = {
            "latitude": 48.1351,
            "longitude": 11.582,
            "hourly": {
                "time": times,
                "temperature_2m": temps
            }
        }

        url = reverse('weather_api')
        params = {
            'latitude': '48.1351',
            'longitude': '11.582',
            'start_date': '1980-01-01',
            'end_date': '1980-01-02',
            'time': '12:00'
        }

        # Request specific hour for range
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2) # noon 1st Jan and noon 2nd Jan
        self.assertEqual(response.data['results'][0]['temperature'], 13.0)
        self.assertEqual(response.data['results'][1]['temperature'], 37.0)

    def test_api_validation_errors(self):
        url = reverse('weather_api')
        
        # 1. Missing date parameters entirely
        response = self.client.get(url, {'latitude': '48.1351', 'longitude': '11.582'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_parameters', response.data)

        # 2. Invalid date range (start_date after end_date)
        response = self.client.get(url, {
            'latitude': '48.1351',
            'longitude': '11.582',
            'start_date': '1980-01-02',
            'end_date': '1980-01-01'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_range', response.data)

        # 3. Range exceeds 366 days
        response = self.client.get(url, {
            'latitude': '48.1351',
            'longitude': '11.582',
            'start_date': '1980-01-01',
            'end_date': '1981-01-02'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_range', response.data)

        # 4. Date before 1940 (historical limit)
        response = self.client.get(url, {
            'latitude': '48.1351',
            'longitude': '11.582',
            'date': '1939-12-31'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_date', response.data)

        # 5. Future date
        response = self.client.get(url, {
            'latitude': '48.1351',
            'longitude': '11.582',
            'date': '2050-01-01'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_date', response.data)


    def test_city_crud_operations(self):
        list_url = reverse('city-list')
        
        # 1. Create a City (POST)
        data = {
            'name': 'Berlin',
            'latitude': '52.520011',  # Will be normalized
            'longitude': '13.405022'  # Will be normalized
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Berlin')
        self.assertEqual(response.data['latitude'], '52.520000')
        self.assertEqual(response.data['longitude'], '13.405000')

        # 2. List Cities (GET)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        city_id = response.data[0]['id']
        detail_url = reverse('city-detail', args=[city_id])

        # 3. Retrieve City Detail (GET)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Berlin')

        # 4. Update City (PUT)
        update_data = {
            'name': 'Berlin Updated',
            'latitude': '52.5100',
            'longitude': '13.4100'
        }
        response = self.client.put(detail_url, update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Berlin Updated')
        self.assertEqual(response.data['latitude'], '52.510000')

        # 5. Delete City (DELETE)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Confirm deleted
        response = self.client.get(list_url)
        self.assertEqual(len(response.data), 0)

    def test_weather_stats_endpoint(self):
        # Create test WeatherData records across different years & coordinates
        lat1 = Decimal('48.1351')
        lon1 = Decimal('11.5820')
        lat2 = Decimal('52.5200')
        lon2 = Decimal('13.4050')

        # Hottest record in 1980
        WeatherData.objects.create(
            latitude=lat1, longitude=lon1,
            timestamp=datetime(1980, 7, 1, 12, 0, tzinfo=timezone.utc),
            temperature=35.5
        )
        # Coldest record in 2024
        WeatherData.objects.create(
            latitude=lat2, longitude=lon2,
            timestamp=datetime(2024, 1, 15, 6, 0, tzinfo=timezone.utc),
            temperature=-10.2
        )
        # Another record in 1980
        WeatherData.objects.create(
            latitude=lat1, longitude=lon1,
            timestamp=datetime(1980, 1, 1, 12, 0, tzinfo=timezone.utc),
            temperature=0.0
        )

        url = reverse('weather_stats_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify totals and unique locations count
        self.assertEqual(response.data['total_records'], 3)
        self.assertEqual(response.data['unique_locations'], 2)
        
        
        
        # Verify yearly distribution mapping
        self.assertEqual(response.data['yearly_distribution']['1980'], 2)
        self.assertEqual(response.data['yearly_distribution']['2024'], 1)
        
        # Verify hottest and coldest records
        self.assertEqual(response.data['hottest_record']['temperature'], 35.5)
        self.assertEqual(response.data['hottest_record']['latitude'], 48.1351)
        self.assertEqual(response.data['coldest_record']['temperature'], -10.2)
        self.assertEqual(response.data['coldest_record']['latitude'], 52.52)

    def test_health_check_endpoint(self):
        url = reverse('health_check_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertEqual(response.data['database'], 'online')
        self.assertEqual(response.data['cache'], 'online')

    @patch('requests.get')
    def test_api_proxy_bypass_for_distant_coordinates(self, mock_get):
        # Mock API response for Berlin (52.5200, 13.4050) -> > 50km from Munich
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        times = [f"1980-01-01T{i:02d}:00" for i in range(24)]
        temps = [1.0 + float(i) for i in range(24)]
        
        mock_response.json.return_value = {
            "latitude": 52.52,
            "longitude": 13.405,
            "hourly": {
                "time": times,
                "temperature_2m": temps
            }
        }

        url = reverse('weather_api')
        params = {
            'latitude': '52.52',
            'longitude': '13.405',
            'date': '1980-01-01'
        }

        # First request: Cache BYPASS
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('X-Cache'), 'BYPASS')
        self.assertEqual(len(response.data['results']), 24)

        # Database must NOT store these records
        db_count = WeatherData.objects.filter(
            latitude=Decimal('52.5200'),
            longitude=Decimal('13.4050')
        ).count()
        self.assertEqual(db_count, 0)

        # Second request: still BYPASS (mock should be called again)
        response_second = self.client.get(url, params)
        self.assertEqual(response_second.status_code, status.HTTP_200_OK)
        self.assertEqual(response_second.headers.get('X-Cache'), 'BYPASS')

