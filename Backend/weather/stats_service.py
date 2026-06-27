import logging
from django.db import connection
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def format_bytes(size_in_bytes) -> str:
    """
    Formats raw bytes to ZZZ.ZZ format with units B, KB, MB, GB, etc.
    Transitions to the next unit if the value is 1000 or greater.
    """
    if size_in_bytes is None:
        return "0.00 B"
    size = float(size_in_bytes)
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    for unit in units[:-1]:
        if size < 1000.0:
            return f"{size:.2f} {unit}"
        size /= 1000.0
    return f"{size:.2f} {units[-1]}"

def get_weather_statistics() -> Dict[str, Any]:
    """
    Fetches weather statistics using raw SQL queries for transparency.
    """
    stats = {
        "total_records": 0,
        "unique_locations": 0,
        "table_storage": {
            "data_size": "0.00 B",
            "index_size": "0.00 B",
            "total_size": "0.00 B"
        },
        "yearly_distribution": {},
        "hottest_record": None,
        "coldest_record": None
    }
    
    try:
        with connection.cursor() as cursor:
            # 1. Total Records
            cursor.execute("SELECT COUNT(*) FROM weather_weatherdata;")
            row = cursor.fetchone()
            if row:
                stats["total_records"] = row[0]

            # 2. Unique Locations Count
            cursor.execute("SELECT COUNT(*) FROM (SELECT DISTINCT latitude, longitude FROM weather_weatherdata) as temp;")
            row = cursor.fetchone()
            if row:
                stats["unique_locations"] = row[0]

            # 3. Database Storage size (PostgreSQL specific)
            if connection.vendor == 'postgresql':
                cursor.execute("SELECT to_regclass('weather_weatherdata');")
                if cursor.fetchone()[0] is not None:
                    cursor.execute("SELECT pg_relation_size('weather_weatherdata');")
                    raw_data_size = cursor.fetchone()[0]
                    cursor.execute("SELECT pg_indexes_size('weather_weatherdata');")
                    raw_index_size = cursor.fetchone()[0]
                    cursor.execute("SELECT pg_total_relation_size('weather_weatherdata');")
                    raw_total_size = cursor.fetchone()[0]
                    
                    stats["table_storage"]["data_size"] = format_bytes(raw_data_size)
                    stats["table_storage"]["index_size"] = format_bytes(raw_index_size)
                    stats["table_storage"]["total_size"] = format_bytes(raw_total_size)
            
            # 4. Yearly distribution
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    SELECT EXTRACT(YEAR FROM timestamp) as year, COUNT(*) 
                    FROM weather_weatherdata 
                    GROUP BY EXTRACT(YEAR FROM timestamp) 
                    ORDER BY year;
                """)
            else:
                # Fallback for SQLite (used in testing)
                cursor.execute("""
                    SELECT strftime('%Y', timestamp) as year, COUNT(*) 
                    FROM weather_weatherdata 
                    GROUP BY strftime('%Y', timestamp) 
                    ORDER BY year;
                """)
                
            for row in cursor.fetchall():
                year = row[0]
                count = row[1]
                if year is not None:
                    # In Postgres, EXTRACT returns float, in SQLite strftime returns str
                    year_str = str(int(year)) if isinstance(year, (float, int)) else str(year)
                    stats["yearly_distribution"][year_str] = count

            # 5. Hottest (Max) Record
            cursor.execute("""
                SELECT temperature, timestamp, latitude, longitude 
                FROM weather_weatherdata 
                ORDER BY temperature DESC 
                LIMIT 1;
            """)
            row = cursor.fetchone()
            if row:
                # row is (temperature, timestamp, latitude, longitude)
                # datetime could be string in sqlite or datetime in postgres
                stats["hottest_record"] = {
                    "temperature": float(row[0]),
                    "timestamp": row[1].isoformat() if hasattr(row[1], 'isoformat') else str(row[1]) + "Z",
                    "latitude": float(row[2]),
                    "longitude": float(row[3])
                }

            # 6. Coldest (Min) Record
            cursor.execute("""
                SELECT temperature, timestamp, latitude, longitude 
                FROM weather_weatherdata 
                ORDER BY temperature ASC 
                LIMIT 1;
            """)
            row = cursor.fetchone()
            if row:
                stats["coldest_record"] = {
                    "temperature": float(row[0]),
                    "timestamp": row[1].isoformat() if hasattr(row[1], 'isoformat') else str(row[1]) + "Z",
                    "latitude": float(row[2]),
                    "longitude": float(row[3])
                }
                
    except Exception as e:
        logger.error(f"Failed to fetch weather statistics using raw SQL: {e}")
        
    return stats
