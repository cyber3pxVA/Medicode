def export_to_csv(data, filename):
    import csv

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data[0].keys())  # Write header
        for row in data:
            writer.writerow(row.values())  # Write data rows


def export_to_json(data, filename):
    import json

    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)