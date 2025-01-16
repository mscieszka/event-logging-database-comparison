import mariadb
import os
# import time
# import random
# import matplotlib.pyplot as plt
from typing import Optional, Dict, List
from datetime import datetime
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
        # self.org: str = os.environ['INFLUXDB_ORG'],

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
