import json
import matplotlib.pyplot as plt
import pandas as pd

json_files = ['span_duration_data_create.json', 'span_duration_data_delete.json', 'span_duration_data_get_all.json', 'span_duration_data_get_country.json', 'span_duration_data_get_severity.json', 'span_duration_data_update.json']

for json_file in json_files:
    with open(json_file, encoding='utf-8-sig') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # Sort the DataFrame by 'span'
    df = df.sort_values(by='span')

    # Create a new figure for each JSON file
    plt.figure(figsize=(12, 6))

    # Plot the data as points without lines
    plt.scatter(df['span'], df['duration'], marker='o')
    plt.xlabel('Span')
    plt.ylabel('Duration (ms)')
    plt.title(f'Span vs Duration - {json_file}')
    plt.grid(True)

    # Set x-ticks to show numbers every 50,000
    plt.xticks(range(0, max(df['span']) + 1, 50000), rotation=45)

    # Adjust layout to ensure the lower description is fully visible
    plt.tight_layout(pad=3.0)

    # Save the figure as a separate image file
    plt.savefig(f'{json_file.split(".")[0]}.png')

    plt.show()
