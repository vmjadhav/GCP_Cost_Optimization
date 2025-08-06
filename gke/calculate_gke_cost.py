from google.cloud import bigquery
from google.auth import default
from datetime import datetime, timedelta
from config import SERVICE_ACCOUNT_KEY
import os

# Set up authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_KEY

# Configuration
PROJECT_ID = "your-project-id"  # Replace with your GCP project ID
BILLING_DATASET = "your_billing_dataset"  # Replace with your billing dataset name
BILLING_TABLE = "gcp_billing_export_v1_XXXXXX"  # Replace with your billing table name

def calculate_gke_costs(project_id, dataset, table, days=30):
    """
    Calculate GKE costs for a given project over the last N days.
    """
    # Initialize BigQuery client
    credentials, _ = default()
    client = bigquery.Client(project=project_id, credentials=credentials)

    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # BigQuery SQL query to fetch GKE costs
    query = f"""
    SELECT
        service.description AS service_description,
        sku.description AS sku_description,
        SUM(cost) AS total_cost,
        ARRAY_AGG(DISTINCT labels.key) AS label_keys
    FROM
        `{dataset}.{table}`
    WHERE
        project.id = @project_id
        AND service.description LIKE '%Kubernetes Engine%'
        AND usage_start_time >= TIMESTAMP(@start_date)
        AND usage_start_time < TIMESTAMP(@end_date)
    GROUP BY
        service.description, sku.description
    """

    # Set query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("project_id", "STRING", project_id),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    # Execute query
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    # Process results
    total_gke_cost = 0.0
    print("GKE Costs Breakdown (Last 30 Days):")
    print("-" * 50)
    for row in results:
        print(f"Service: {row.service_description}")
        print(f"SKU: {row.sku_description}")
        print(f"Cost: ${row.total_cost:.2f}")
        print(f"Labels: {row.label_keys}")
        print("-" * 50)
        total_gke_cost += row.total_cost

    print(f"Total GKE Cost: ${total_gke_cost:.2f}")
    return total_gke_cost

def main():
    try:
        total_cost = calculate_gke_costs(PROJECT_ID, BILLING_DATASET, BILLING_TABLE)
        return total_cost
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return None

if __name__ == "__main__":
    main()