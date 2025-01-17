import time
import requests
from influx.models import Utilities

host = "http://localhost:8000"
runs = 3

# Generate N events with custom time range
events_to_generate = 1
url = f"{host}/influxdb/events"

events_json_influx = []
for _ in range(events_to_generate):
    events_json_influx.append(Utilities.get_random_event_json())

total_time = 0
for _ in range(runs):
    start_time = time.time()
    response = requests.post(
        url=url,
        json=events_json_influx,
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        print(f"Failed with status code {response.status_code}: {response.text}")
    end_time = time.time()
    run_time = end_time - start_time
    total_time += run_time

average_time = total_time / runs
print(f"Average time per run: {average_time:.2f} seconds")


# Clear generated events
url = f"{host}/influxdb/clear-events"
start_time = time.time()
response = requests.post(url)
if response.status_code != 200:
    print(f"Failed with status code {response.status_code}: {response.text}")
end_time = time.time()
clean_time = end_time - start_time
print(f"Cleaned in {average_time:.2f} seconds")
