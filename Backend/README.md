# Weather Backend Coding Challenge

A clean, production-ready Django REST Framework backend designed to fetch, cache, and serve historical weather data. Connects to PostgreSQL for persistence and uses Django's fast memory caching.

## Features
- **Interactive API Documentation (Swagger):** Fully documented API with Swagger UI (`/api/schema/swagger-ui/`) and Redoc (`/api/schema/redoc/`).
- **Historical Weather Integration:** Integrates with the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api).
- **Dual-Layer Caching:**
  1. **PostgreSQL Cache:** Saves fetched weather data to prevent redundant external API calls (especially for the Greater Munich Area).
  2. **Memory Cache:** Serves consecutive identical API requests instantly with custom cache keys.
- **Robust Model Layer:** Employs constraints to prevent duplicate entries and indexes to speed up lookups.
- **Custom CLI Command:** Pre-populates the database with Munich's noon temperatures for the entire year of 1980 in a single command.
- **Full Test Coverage:** Unit and integration tests covering the service logic, serializers, views, validation, and caching.

---

## Setup Instructions

### 1. Prerequisites
- **Python 3.13+**
- **Docker** running your PostgreSQL and Redis instances.

### 2. Virtual Environment & Dependencies
Create the environment and install packages:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Verify that the `.env` file exists in the root directory. It is configured with the following credentials (matching your Docker setup):
```ini
# Django Settings
SECRET_KEY=django-insecure-weather-backend-challenge-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL Settings
DB_NAME=postgres
DB_USER=myuser
DB_PASSWORD=UaY7XePH97S98KXlNVbLca4DTu7LtBt6
DB_HOST=localhost
DB_PORT=5432

# Redis Cache Settings
REDIS_URL=redis://:aLxo8ZjmKhFNMSNZPNeph8lCAOnOEBbnOuMjuox@localhost:6379/0
```

---

## Running the Project

### 1. Database Migrations
Create and apply migrations to build the tables in PostgreSQL:
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 2. Pre-Populate 1980 Munich Data
Run the custom management command to cache 1980 noon temperatures for Munich:
```powershell
python manage.py fetch_munich_1980
```

### 3. Start the Server
Start the Django development server:
```powershell
python manage.py runserver
```
The server will start at `http://127.0.0.1:8000/`.

---

## API Usage

### Endpoint: `GET /api/weather/`
Retrieve weather details for a specific latitude, longitude, and date.

#### Query Parameters:
- `latitude` (Required, float/decimal between -90 and 90)
- `longitude` (Required, float/decimal between -180 and 180)
- `date` (Required if `start_date` and `end_date` not provided, format: `YYYY-MM-DD`)
- `start_date` (Required if `date` not provided, format: `YYYY-MM-DD`)
- `end_date` (Required if `date` not provided, format: `YYYY-MM-DD`)
- `time` (Optional, format: `HH:MM`)

*Note: The maximum supported date range between `start_date` and `end_date` is **1 year (366 days)** to prevent API timeouts and respect external API rate limits.*

#### Example 1: Full Day Temperature History (Single Date)
**Request:**
`GET http://127.0.0.1:8000/api/weather/?latitude=48.1351&longitude=11.582&date=1980-01-01`

**Response:**
```json
{
  "latitude": 48.1351,
  "longitude": 11.582,
  "start_date": "1980-01-01",
  "end_date": "1980-01-01",
  "results": [
    {
      "latitude": "48.135100",
      "longitude": "11.582000",
      "timestamp": "1980-01-01T00:00:00Z",
      "temperature": 1.2
    },
    ...
  ]
}
```

#### Example 2: Date Range Query for an Entire Year (Noon Only)
**Request:**
`GET http://127.0.0.1:8000/api/weather/?latitude=52.52&longitude=13.405&start_date=1980-01-01&end_date=1980-12-31&time=12:00`

**Response:**
```json
{
  "latitude": 52.5200,
  "longitude": 13.4050,
  "start_date": "1980-01-01",
  "end_date": "1980-12-31",
  "results": [
    {
      "latitude": "52.520000",
      "longitude": "13.405000",
      "timestamp": "1980-01-01T12:00:00Z",
      "temperature": -2.3
    },
    {
      "latitude": "52.520000",
      "longitude": "13.405000",
      "timestamp": "1980-01-02T12:00:00Z",
      "temperature": -4.1
    },
    ...
  ]
}
```

#### Response Headers (Caching verification):
- **`X-Cache: MISS`** indicates a fresh request querying the database or external API.
- **`X-Cache: HIT`** indicates the response was served directly and instantly from Redis.

---

## Cities API (CRUD)
You can manage cities (Create, Read, Update, Delete) via the `/api/cities/` endpoints.

### Endpoints:
- **List Cities:** `GET /api/cities/`
- **Create City:** `POST /api/cities/` (Body: `{"name": "Berlin", "latitude": 52.52, "longitude": 13.405}`)
- **Retrieve City:** `GET /api/cities/<id>/`
- **Update City:** `PUT /api/cities/<id>/` (Body: `{"name": "Berlin Updated", "latitude": 52.51, "longitude": 13.41}`)
- **Delete City:** `DELETE /api/cities/<id>/`

*Note: Just like weather coordinates, city coordinates are automatically normalized to 4 decimal places upon saving to ensure database consistency.*

---

## Weather Database Statistics API
Exposes metrics summarizing the contents, size, and historical extremes of the weather database cache.

### Endpoint:
- **Get Statistics:** `GET /api/weather/stats/`

### Example Response:
```json
{
  "total_records": 366,
  "unique_locations": 1,
  "table_storage": {
    "data_size": "56.00 KB",
    "index_size": "64.00 KB",
    "total_size": "120.00 KB"
  },
  "yearly_distribution": {
    "1980": 366
  },
  "hottest_record": {
    "temperature": 18.2,
    "timestamp": "1980-07-20T12:00:00Z",
    "latitude": 48.1351,
    "longitude": 11.582
  },
  "coldest_record": {
    "temperature": -15.4,
    "timestamp": "1980-01-18T12:00:00Z",
    "latitude": 48.1351,
    "longitude": 11.582
  }
}
```

---

## Health Check API
Verifies that the backend has active, working connections to both PostgreSQL and Redis cache.

### Endpoint:
- **Get Health Status:** `GET /api/health/`

### Example Response:
```json
{
  "status": "healthy",
  "database": "online",
  "redis": "online"
}
```

---

## Historical Munich Data Pre-population Script
A standalone script `fetch_munich_1940_2026.py` is included in the project root to fetch Munich's noon (12:00) weather records from 1940 to 2026.

### How to Run:
```powershell
python fetch_munich_1940_2026.py
```

*Note: This script divides requests into 10-year intervals to ensure connection stability and avoid timeouts. It uses `bulk_create` with conflict ignoring to ensure duplicate records are not added.*

---

## Running Tests

Execute Django's testing suite to run all tests:
```powershell
python manage.py test
```



