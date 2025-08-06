from google.cloud import logging_v2
from datetime import datetime, timedelta

def query_gcs_access_logs(project_id, bucket_name, days=30):
    client = logging_v2.Client(project=project_id)
    logger = client.logger('cloudaudit.googleapis.com%2Fdata_access')  # audit logs for data access

    # Construct filter string
    filter_str = (
        f'resource.type="gcs_bucket" AND '
        f'protoPayload.serviceName="storage.googleapis.com" AND '
        f'protoPayload.methodName="storage.objects.get" AND '
        f'protoPayload.resourceName:"projects/_/buckets/{bucket_name}" AND '
        f'timestamp >= "{(datetime.utcnow() - timedelta(days=days)).isoformat("T")}Z"'
    )

    # Query entries
    entries = client.list_entries(filter_=filter_str)

    access_counts = {}

    for entry in entries:
        resource_name = entry.payload.get('resourceName', '')
        access_counts[resource_name] = access_counts.get(resource_name, 0) + 1

    return access_counts

# Example usage
if __name__ == "__main__":
    project_id = 'your-project-id'
    bucket_name = 'your-data-bucket'
    counts = query_gcs_access_logs(project_id, bucket_name)
    for resource, count in counts.items():
        print(f"{resource}: {count} accesses in last 30 days")
