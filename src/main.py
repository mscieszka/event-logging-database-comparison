import mariadb
import random
import os
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from influx.manager import InfluxDBManager
from influx.models import Event, UpdateEventSeverity, SAMPLE_DATA, Severity, EventType, Source

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

@app.post("/influxdb/event/")
async def create_event(event: Event):
    timestamp_start = datetime.now()
    success = influxdb.write_event(event)
    timestamp_end = datetime.now()
    total_milliseconds = int(timestamp_end.timestamp() * 1000) - int(timestamp_start.timestamp() * 1000)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write event to database")

    return {"total_milliseconds": total_milliseconds, "message": "Event logged successfully"}

@app.post("/influxdb/events/")
async def create_event(events: List[Event]):
    timestamp_start = datetime.now()
    success = influxdb.write_events_batch(events)
    timestamp_end = datetime.now()
    total_milliseconds = int(timestamp_end.timestamp() * 1000) - int(timestamp_start.timestamp() * 1000)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write events to database")

    return {"total_milliseconds": total_milliseconds, "message": "Events logged successfully"}

@app.get("/influxdb/events/")
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

    timestamp_start = datetime.now()
    events = influxdb.query_events(start_time, end_time, filters)
    timestamp_end = datetime.now()
    total_milliseconds = int(timestamp_end.timestamp() * 1000) - int(timestamp_start.timestamp() * 1000)

    return {"total_milliseconds": total_milliseconds, "events": events}

@app.delete("/influxdb/clear-events/")
async def clear_events_influxdb(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """
    Clear events from the InfluxDB bucket within the given time range.
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(days=1080)
    if end_time is None:
        end_time = datetime.now() + timedelta(days=1)
    try:
        timestamp_start = datetime.now()
        influxdb.delete_api.delete(
            start=start_time,
            stop=end_time,
            bucket=influxdb.bucket,
            org=influxdb.client.org,
            predicate='_measurement="events"'
        )
        timestamp_end = datetime.now()
        total_milliseconds = int(timestamp_end.timestamp() * 1000) - int(timestamp_start.timestamp() * 1000)

        return {"total_milliseconds": total_milliseconds, "message": "Events cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing events: {e}")

@app.put("/influxdb/event/severity")
async def update_event_severity(request: UpdateEventSeverity):
    timestamp_start = datetime.now()
    success = influxdb.update_event_severity(
        timestamp=request.timestamp,
        old_severity=request.old_severity,
        new_severity=request.new_severity,
        event_type=request.event_type,
        source_name=request.source_name
    )
    timestamp_end = datetime.now()
    total_milliseconds = int(timestamp_end.timestamp() * 1000) - int(timestamp_start.timestamp() * 1000)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Event not found or failed to update severity"
        )

    return {"total_milliseconds": total_milliseconds, "message": f"Event severity updated successfully."}


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
        start_time = datetime.now() - timedelta(days=30)
    if end_time is None:
        end_time = datetime.now()

    events = []
    for _ in range(events_to_generate):
        # Generate reference time within the specified range
        reference_time = start_time + (end_time - start_time) * random.random()

        # Get events data
        events.append(generate_random_event(reference_time))

    timestamp_start = datetime.now()
    success = influxdb.write_events_batch(events)
    timestamp_end = datetime.now()
    total_milliseconds = int(timestamp_end.timestamp() * 1000) - int(timestamp_start.timestamp() * 1000)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write events to database")

    return {"total_milliseconds": total_milliseconds, "message": f"Generated events successfully.",}

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
