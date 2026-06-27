# Weather Backend Coding Challenge

A clean, production-ready Django REST Framework backend designed to fetch, cache, and serve historical weather data. Connects to PostgreSQL for persistence and Redis for caching.

## Features
- **Historical Weather Integration:** Integrates with the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api).
- **Dual-Layer Caching:**
  1. **PostgreSQL Cache:** Saves fetched weather data to prevent redundant external API calls (especially for the Greater Munich Area).
  2. **Redis Cache:** Serves consecutive identical API requests instantly with custom cache keys.
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
- `date` (Required, format: `YYYY-MM-DD`)
- `time` (Optional, format: `HH:MM`)

#### Example 1: Full Day Temperature History (24 hours)
**Request:**
`GET http://127.0.0.1:8000/api/weather/?latitude=48.1351&longitude=11.582&date=1980-01-01`

**Response:**
```json
{
  "latitude": 48.1351,
  "longitude": 11.582,
  "date": "1980-01-01",
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

#### Example 2: Specific Hour Temperature
**Request:**
`GET http://127.0.0.1:8000/api/weather/?latitude=48.1351&longitude=11.582&date=1980-01-01&time=12:00`

**Response:**
```json
{
  "latitude": 48.1351,
  "longitude": 11.582,
  "date": "1980-01-01",
  "results": [
    {
      "latitude": "48.135100",
      "longitude": "11.582000",
      "timestamp": "1980-01-01T12:00:00Z",
      "temperature": -0.8
    }
  ]
}
```

#### Response Headers (Caching verification):
- **`X-Cache: MISS`** indicates a fresh request querying the database or external API.
- **`X-Cache: HIT`** indicates the response was served directly and instantly from Redis.

---

## Running Tests

Execute Django's testing suite to run all tests:
```powershell
python manage.py test
```
