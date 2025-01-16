import time
import requests

# Generate N events with custom time range
events_to_generate = 10^9
url = f"http://localhost:8000/generate-events/?events_to_generate={events_to_generate}&start_time=2025-01-10T00:00:00Z&end_time=2025-01-14T00:00:00Z"
runs = 3

start_time = time.time()
for _ in range(runs):
    response = requests.post(url)
    if response.status_code != 200:
        print(f"Failed with status code {response.status_code}: {response.text}")
end_time = time.time()

total_time = end_time - start_time
average_time = total_time / runs

print(f"Average time per run: {average_time:.2f} seconds")

# Clear generated events
url = f"http://localhost:8000/clear-events/?start_time=2025-01-09T00:00:00Z&end_time=2025-01-14T00:00:00Z"
response = requests.post(url)
if response.status_code != 200:
    print(f"Failed with status code {response.status_code}: {response.text}")
