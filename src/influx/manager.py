import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WriteOptions

from src.influx.models import Event

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
            point = self.create_event_point(event)
            self.write_api.write(bucket=self.bucket, org=self.client.org, record=point)
            return True
        except Exception as e:
            print(f"Error writing to InfluxDB: {e}")
            return False

    def write_events_batch(self, events: List[Event]):
        points = []
        for event in events:
            point = self.create_event_point(event)
            points.append(point)
        try:
            self.write_api.write(bucket=self.bucket, org=self.client.org, record=points)
            return True
        except Exception as e:
            print(f"Error writing to InfluxDB: {e}")
            return False

    def create_event_point(self, event: Event):
        point = Point("events").time(event.timestamp)
        point.tag("severity", event.severity.name)
        point.tag("event_type", event.event_type.name)
        point.tag("source_name", event.source.name)
        point.tag("source_ip", event.source.ip_address)
        point.tag("location_country", event.source.location.country)
        point.tag("location_city", event.source.location.city)
        point.field("message", event.message)

        return point

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

    def update_event_severity(self, timestamp: datetime, old_severity: str, new_severity: str,
                              event_type: str, source_name: str) -> bool:
        try:
            # First query to get the existing event
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: {timestamp.isoformat()}, stop: {(timestamp + timedelta(seconds=1)).isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "events")
                |> filter(fn: (r) => r["severity"] == "{old_severity}")
                |> filter(fn: (r) => r["event_type"] == "{event_type}")
                |> filter(fn: (r) => r["source_name"] == "{source_name}")
            '''

            query_api = self.client.query_api()
            result = query_api.query(org=self.client.org, query=query)

            if not result or len(result) == 0:
                return False

            # Get the existing event data
            record = result[0].records[0]

            # Create a new point with updated severity
            point = Point("events") \
                .time(timestamp) \
                .tag("severity", new_severity) \
                .tag("event_type", event_type) \
                .tag("source_name", source_name) \
                .tag("source_ip", record.values.get("source_ip")) \
                .tag("location_country", record.values.get("location_country")) \
                .tag("location_city", record.values.get("location_city")) \
                .field("message", record.get_value())

            # Delete the old point
            self.delete_api.delete(
                start=timestamp,
                stop=timestamp + timedelta(seconds=1),
                bucket=self.bucket,
                org=self.client.org,
                predicate=f'_measurement="events" and severity="{old_severity}" and event_type="{event_type}" and source_name="{source_name}"'
            )

            # Write the new point
            self.write_api.write(bucket=self.bucket, org=self.client.org, record=point)
            return True

        except Exception as e:
            print(f"Error updating event severity in InfluxDB: {e}")
            return False
