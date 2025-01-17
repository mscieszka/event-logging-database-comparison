import mariadb
import os
# import matplotlib.pyplot as plt
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from influx.manager import InfluxDBManager
from influx.models import Event, UpdateEventSeverity

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
    success = influxdb.write_event(event)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write event to database")
    return {"message": "Event logged successfully"}

@app.post("/influxdb/events/")
async def create_event(events: List[Event]):
    success = influxdb.write_events_batch(events)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write events to database")
    return {"message": "Events logged successfully"}

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

    events = influxdb.query_events(start_time, end_time, filters)
    return {"events": events}

@app.post("/influxdb/clear-events/")
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

@app.put("/influxdb/event/severity")
async def update_event_severity(request: UpdateEventSeverity):
    success = influxdb.update_event_severity(
        timestamp=request.timestamp,
        old_severity=request.old_severity,
        new_severity=request.new_severity,
        event_type=request.event_type,
        source_name=request.source_name
    )
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Event not found or failed to update severity"
        )

    return {"message": "Event severity updated successfully"}
