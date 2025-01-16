import mariadb
import os
import random
# import matplotlib.pyplot as plt
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class Location(BaseModel):
    name: str
    country: str
    city: str

class Source(BaseModel):
    name: str
    ip_address: str
    location: Location

class EventType(BaseModel):
    name: str
    description: str

class Severity(BaseModel):
    name: str
    description: str

class Event(BaseModel):
    timestamp: datetime
    message: str
    severity: Severity
    event_type: EventType
    source: Source

class InfluxDBManager:

    def get_influxdb_client(self):
        try:
            self.client = InfluxDBClient(
                url='http://influxdb:8086',
                token=os.environ['INFLUXDB_TOKEN'],
                username=os.environ['INFLUXDB_USER'],
                password=os.environ['INFLUXDB_PASSWORD'],
                org=os.environ['INFLUXDB_ORG'],
                ssl=True,
                verify_ssl=True,
            )
        except Exception as e:
            print(f"Error: {e}")
            return False

        return self.client

    def __init__(self):
        self.client = self.get_influxdb_client()
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = os.getenv('INFLUXDB_BUCKET')
        self.delete_api = self.client.delete_api()

    def write_event(self, event: Event) -> bool:
        try:
            point = Point("events") \
                .time(event.timestamp) \
                .tag("severity", event.severity.name) \
                .tag("event_type", event.event_type.name) \
                .tag("source_name", event.source.name) \
                .tag("source_ip", event.source.ip_address) \
                .tag("location_country", event.source.location.country) \
                .tag("location_city", event.source.location.city) \
                .field("message", event.message)

            self.write_api.write(bucket=self.bucket, org=self.client.org, record=point)
            return True
        except Exception as e:
            print(f"Error writing to InfluxDB: {e}")
            return False

    def query_events(
            self,
            start_time: datetime,
            end_time: datetime,
            filters: Optional[Dict] = None
    ) -> List[Dict]:
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
            |> filter(fn: (r) => r["_measurement"] == "events")
        '''

        if filters:
            for key, value in filters.items():
                query += f'|> filter(fn: (r) => r["{key}"] == "{value}")'

        query += '|> yield(name: "results")'

        try:
            query_api = self.client.query_api()
            result = query_api.query(org=self.client.org, query=query)

            events = []
            for table in result:
                for record in table.records:
                    events.append({
                        "timestamp": record.get_time(),
                        "message": record.get_value(),
                        "severity": record.values.get("severity"),
                        "event_type": record.values.get("event_type"),
                        "source_name": record.values.get("source_name"),
                        "source_ip": record.values.get("source_ip"),
                        "location_country": record.values.get("location_country"),
                        "location_city": record.values.get("location_city")
                    })
            return events
        except Exception as e:
            print(f"Error querying InfluxDB: {e}")
            return []

def get_mariadb_connection():
    try:
        connection = mariadb.connect(
            host=os.environ['MARIADB_HOST'],
            user=os.environ['MARIADB_USER'],
            password=os.environ['MARIADB_PASSWORD'],
            database=os.environ['MARIADB_DATABASE'],
        )
    except mariadb.Error as e:
        print(f"Error: {e}")
        return False

    return connection

app = FastAPI()
influxdb = InfluxDBManager()

@app.post("/events/")
async def create_event(event: Event):
    success = influxdb.write_event(event)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write event to database")
    return {"message": "Event logged successfully"}

@app.get("/events/")
async def get_events(
        start_time: datetime,
        end_time: datetime,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        source_name: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None
):
    filters = {}
    if severity:
        filters["severity"] = severity
    if event_type:
        filters["event_type"] = event_type
    if source_name:
        filters["source_name"] = source_name
    if country:
        filters["location_country"] = country
    if city:
        filters["location_city"] = city

    events = influxdb.query_events(start_time, end_time, filters)
    return {"events": events}

# Sample data for event generation
SAMPLE_DATA = {
    "severities": [
        {"name": "INFO", "description": "Informational message"},
        {"name": "WARNING", "description": "Warning condition"},
        {"name": "ERROR", "description": "Error condition"},
        {"name": "CRITICAL", "description": "Critical condition"}
    ],
    "event_types": [
        {"name": "SYSTEM_STATUS", "description": "System status update"},
        {"name": "SECURITY_ALERT", "description": "Security-related event"},
        {"name": "PERFORMANCE", "description": "Performance metric event"},
        {"name": "USER_ACTION", "description": "User-initiated action"},
    ],
    "sources": [
        {
            "name": "web-server-01",
            "ip_address": "192.168.1.100",
            "location": {"name": "PL-01", "country": "Poland", "city": "Katowice"}
        },
        {
            "name": "web-server-02",
            "ip_address": "192.168.1.200",
            "location": {"name": "PL-02", "country": "Poland", "city": "Gdansk"}
        },
        {
            "name": "cache-01",
            "ip_address": "192.168.2.100",
            "location": {"name": "US-01", "country": "USA", "city": "New York"}
        },
        {
            "name": "lb-01",
            "ip_address": "192.168.3.100",
            "location": {"name": "DE-01", "country": "Germany", "city": "Frankfurt"}
        }
    ],
    "messages": {
        "SYSTEM_STATUS": [
            "System startup completed",
            "System shutdown initiated",
            "Service restart required",
            "Memory usage at {}%",
            "CPU utilization peaked at {}%"
        ],
        "SECURITY_ALERT": [
            "Failed login attempt from IP {}",
            "Suspicious activity detected",
            "Firewall rule updated",
            "New security patch applied",
            "User account locked after {} attempts"
        ],
        "PERFORMANCE": [
            "Response time exceeded {}ms",
            "Database query took {}ms",
            "Network latency increased to {}ms",
            "Queue size reached {}"
        ],
        "USER_ACTION": [
            "User {} logged in successfully",
            "Password change attempted",
            "Configuration updated by admin",
            "New user account created"
        ],
    }
}

def generate_random_event(reference_time: Optional[datetime] = None) -> Event:
    if reference_time is None:
        reference_time = datetime.now()

    # Add time variation (±12 hours)
    time_variation = timedelta(hours=random.uniform(-12, 12))
    timestamp = reference_time + time_variation

    # Select event components
    severity = random.choice(SAMPLE_DATA["severities"])
    event_type = random.choice(SAMPLE_DATA["event_types"])
    source = random.choice(SAMPLE_DATA["sources"])

    # Generate message with random parameters
    message_template = random.choice(SAMPLE_DATA["messages"][event_type["name"]])
    message = message_template.format(
        *[random.randint(1, 100) for _ in range(message_template.count("{}"))]
    )

    return Event(
        timestamp=timestamp,
        message=message,
        severity=Severity(**severity),
        event_type=EventType(**event_type),
        source=Source(**source)
    )

@app.post("/generate-events/")
async def generate_events(
        events_to_generate: int = 10,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
):
    """
    Generate and store random events.
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(days=3)
    if end_time is None:
        end_time = datetime.now()

    generated_events = []
    for _ in range(events_to_generate):
        # Generate reference time within the specified range
        reference_time = start_time + (end_time - start_time) * random.random()
        event = generate_random_event(reference_time)

        # Store event in InfluxDB
        success = influxdb.write_event(event)
        if success:
            generated_events.append({
                "timestamp": event.timestamp,
                "message": event.message,
                "severity": event.severity.name,
                "event_type": event.event_type.name,
                "source": event.source.name
            })

    return {
        "message": f"Generated {len(generated_events)} events",
        "events": generated_events
    }

@app.post("/clear-events/")
async def clear_events(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """
    Clear events from the InfluxDB bucket within the given time range.
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(days=10)
    if end_time is None:
        end_time = datetime.now()
    try:
        influxdb.delete_api.delete(
            start=start_time,
            stop=end_time,
            bucket=influxdb.bucket,
            org=influxdb.client.org,
            predicate='_measurement="events"'
        )
        return {"message": "Events cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing events: {e}")
