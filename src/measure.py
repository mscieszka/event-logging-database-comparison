import json
import time
import requests
from influx.models import Utilities

host = "http://localhost:8000"
runs = 3
# spans = [1, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000]
# spans = [1, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000]
spans = [1, 10, 50]

def measure_create_delete():
    global url, span, __, response, response_data, run_time_milliseconds, file
    url = f"{host}/influxdb/events"
    data_create = []
    data_delete = []
    for span in spans:
        create_runs_time = 0
        delete_runs_time = 0
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
            create_runs_time += run_time_milliseconds

            # Clear generated events
            url = f"{host}/influxdb/clear-events"
            response = requests.post(url)
            if response.status_code != 200:
                print(f"Failed with status code {response.status_code}: {response.text}")
            response_data = response.json()
            delete_runs_time += response_data.get("total_milliseconds")

        create_average_span_time = create_runs_time / runs
        data_create.append({"span": span, "duration": create_average_span_time})

        delete_average_span_time = delete_runs_time / runs
        data_delete.append({"span": span, "duration": delete_average_span_time})


    with open("span_duration_data_create.json", "w") as file:
        file.write(json.dumps(data_create))
    with open("span_duration_data_delete.json", "w") as file:
        file.write(json.dumps(data_delete))

def measure_update_get():
    global span, url, response, __, response_data, run_time_milliseconds, file
    data_update = []
    data_get_all = []
    data_get_severity = []
    for span in spans:
        # Create span-1 events.
        url = f"{host}/generate-events?events_to_generate={span - 1}"
        response = requests.post(url=url)
        if response.status_code != 200:
            print(f"Failed with status code {response.status_code}: {response.text}")

        runs_time_update = 0
        runs_time_get_all = 0
        runs_time_get_severity = 0
        for __ in range(runs):
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

            # Find all events
            url = f"{host}/influxdb/events?end_time=2025-01-18T10:00:00Z&start_time=2023-01-01T10:00:00Z"
            response = requests.get(url=url)
            if response.status_code != 200:
                print(f"Failed with status code {response.status_code}: {response.text}")
            response_data = response.json()
            runs_time_get_all += response_data.get("total_milliseconds")

            # Find all events with a given severity
            url = f"{host}/influxdb/events?end_time=2025-01-18T10:00:00Z&start_time=2023-01-01T10:00:00Z&severity=INFO"
            response = requests.get(url=url)
            if response.status_code != 200:
                print(f"Failed with status code {response.status_code}: {response.text}")
            response_data = response.json()
            runs_time_get_severity += response_data.get("total_milliseconds")

            # Update one event
            time.sleep(0.5)
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

            # Remove custom event
            url = f"{host}/influxdb/clear-events?start_time=2025-01-15T10:00:00Z&end_time=2025-01-15T10:00:00Z"
            response = requests.post(url)
            if response.status_code != 200:
                print(f"Failed with status code {response.status_code}: {response.text}")

        average_span_time_update = runs_time_update / runs
        data_update.append({"span": span, "duration": average_span_time_update})

        average_span_time_get_all = runs_time_get_all / runs
        data_get_all.append({"span": span, "duration": average_span_time_get_all})

        average_span_time_get_severity = runs_time_get_severity / runs
        data_get_severity.append({"span": span, "duration": average_span_time_get_severity})

        # Clear generated events
        url = f"{host}/influxdb/clear-events"
        response = requests.post(url)
        if response.status_code != 200:
            print(f"Failed with status code {response.status_code}: {response.text}")

    with open("span_duration_data_update.json", "w") as file:
        file.write(json.dumps(data_update))
    with open("span_duration_data_get_all.json", "w") as file:
        file.write(json.dumps(data_get_all))
    with open("span_duration_data_get_severity.json", "w") as file:
        file.write(json.dumps(data_get_severity))

measure_create_delete()
# measure_update_get()
