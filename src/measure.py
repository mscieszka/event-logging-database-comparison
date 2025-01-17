import json
import time
import requests
from influx.models import Utilities

host = "http://localhost:8000"
runs = 3
# spans = [1, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000]
spans = [1, 10, 50]


def measure_create():
    global url, span, __, response, response_data, run_time_milliseconds, file
    url = f"{host}/influxdb/events"
    data_create = []
    for span in spans:
        all_runs_time = 0
        events_json_influx = []
        for _ in range(span):
            events_json_influx.append(Utilities.get_random_event_json())
        for __ in range(runs):
            response = requests.post(
                url=url,
                json=events_json_influx,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                print(f"Failed with status code {response.status_code}: {response.text}")
            response_data = response.json()
            run_time_milliseconds = response_data.get("total_milliseconds")
            all_runs_time += run_time_milliseconds

        average_span_time = all_runs_time / runs
        data_create.append({"span": span, "duration": average_span_time})
    with open("span_duration_data_create.json", "w") as file:
        file.write(json.dumps(data_create))

def measure_update_delete():
    global span, url, response, __, response_data, run_time_milliseconds, file
    data_update = []
    data_delete = []
    for span in spans:
        # Create span-1 events.
        url = f"{host}/generate-events?events_to_generate={span - 1}"
        response = requests.post(url=url)
        if response.status_code != 200:
            print(f"Failed with status code {response.status_code}: {response.text}")

        # Add one event with custom data.
        url = f"{host}/influxdb/event"
        event_data = {
            "timestamp": "2025-01-15T10:00:00Z",
            "message": "System startup completed",
            "severity": {
                "name": "INFO",
                "description": "Informational message"
            },
            "event_type": {
                "name": "SYSTEM_STATUS",
                "description": "System status update"
            },
            "source": {
                "name": "web-server-01",
                "ip_address": "192.168.1.100",
                "location": {
                    "name": "DC-North",
                    "country": "USA",
                    "city": "Chicago"
                }
            }
        }
        response = requests.post(
            url=url,
            json=event_data
        )
        if response.status_code != 200:
            print(f"Failed with status code {response.status_code}: {response.text}")

        time.sleep(0.5)
        runs_time_update = 0
        runs_time_delete = 0
        for __ in range(runs):
            # Update one event
            url = f"{host}/influxdb/event/severity"
            event_update_data = {
                "timestamp": "2025-01-15T10:00:00Z",
                "old_severity": "INFO",
                "new_severity": "ERROR",
                "event_type": "SYSTEM_STATUS",
                "source_name": "web-server-01"
            }
            response = requests.put(
                url=url,
                json=event_update_data
            )
            if response.status_code != 200:
                print(f"Failed with status code {response.status_code}: {response.text}")
            response_data = response.json()
            run_time_milliseconds = response_data.get("total_milliseconds")
            runs_time_update += run_time_milliseconds

            # Clear generated events
            url = f"{host}/influxdb/clear-events"
            response = requests.post(url)
            if response.status_code != 200:
                print(f"Failed with status code {response.status_code}: {response.text}")
            response_data = response.json()
            run_time_milliseconds = response_data.get("total_milliseconds")
            runs_time_delete += run_time_milliseconds
        average_span_time_update = runs_time_update / runs
        average_span_time_delete = runs_time_delete / runs
        data_update.append({"span": span, "duration": average_span_time_update})
        data_delete.append({"span": span, "duration": average_span_time_delete})
    with open("span_duration_data_update.json", "w") as file:
        file.write(json.dumps(data_update))
    with open("span_duration_data_delete.json", "w") as file:
        file.write(json.dumps(data_delete))


# measure_create()
measure_update_delete()
