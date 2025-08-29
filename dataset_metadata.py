from google.cloud import storage

def get_gcs_data_points(bucket_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    data_points = []
    blobs = bucket.list_blobs()

    for blob in blobs:
        # blob.size is the size in bytes
        size_gb = blob.size / (1024**3) if blob.size else 0

        # Access frequency might not be directly available in storage metadata;
        # for example, you could use object custom metadata if you store access counts,
        # or use logs/statistics from Cloud Monitoring / Logging
        access_frequency = 0  # Placeholder, see point below

        data_points.append({
            'name': blob.name,
            'size_gb': size_gb,
            'access_frequency': access_frequency,
            # Depending on your metadata design, you could add other info here
        })

    return data_points

# Example usage:
bucket_name = "your-bucket-name"
datasets_info = get_gcs_data_points(bucket_name)

for dataset in datasets_info:
    print(f"Object: {dataset['name']}, Size (GB): {dataset['size_gb']}, Access Frequency: {dataset['access_frequency']}")
