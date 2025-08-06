from google.cloud import bigquery
from datetime import datetime, timedelta


def calculate_bigquery_costs(project_id, billing_dataset, billing_table):
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)

    # Define pricing constants (US region, as of 2025)
    active_storage_cost_per_gb = 0.02  # $0.02/GB/month
    long_term_storage_cost_per_gb = 0.01  # $0.01/GB/month
    query_cost_per_tb = 5.0  # $5/TB
    streaming_cost_per_gb = 0.05  # $0.05/GB
    egress_cost_per_gb = 0.12  # $0.12/GB
    free_storage_gb = 10  # 10 GB free storage
    free_query_tb = 1  # 1 TB free query processing

    # Query billing data for the last 30 days
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    query = f"""
    SELECT
        service.description,
        sku.description,
        SUM(cost) as total_cost,
        SUM(usage.amount) as total_usage,
        usage.unit
    FROM `{billing_dataset}.{billing_table}`
    WHERE
        service.description = 'BigQuery'
        AND invoice.month = FORMAT_TIMESTAMP('%Y%m', CURRENT_TIMESTAMP())
        AND usage_start_time >= TIMESTAMP('{start_date}')
    GROUP BY service.description, sku.description, usage.unit
    """
    query_job = client.query(query)
    results = query_job.result()

    # Initialize cost breakdown
    storage_cost = 0.0
    query_cost = 0.0
    streaming_cost = 0.0
    egress_cost = 0.0


    # Process billing data
    for row in results:
        if 'Storage' in row.sku_description:
            # Storage costs (active or long-term)
            if 'Long-term' in row.sku_description:
                storage_cost += row.total_cost
            else:
                storage_cost += max(0, row.total_cost - (free_storage_gb * active_storage_cost_per_gb))
        elif 'Analysis' in row.sku_description:
            query_cost += max(0, row.total_cost - (free_query_tb * query_cost_per_tb))
        elif 'Streaming' in row.sku_description:
            streaming_cost += row.total_cost
        elif 'Egress' in row.sku_description:
            egress_cost += row.total_cost

    # Query INFORMATION_SCHEMA for detailed query usage (optional)
    query_usage = f"""
    SELECT
        SUM(total_bytes_processed) / POW(10, 12) as total_tb_processed
    FROM `{project_id}.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
    WHERE
        job_type = 'QUERY'
        AND state = 'DONE'
        AND creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    """
    query_job = client.query(query_usage)
    query_tb = next(query_job.result()).total_tb_processed
    query_cost_estimate = max(0, (query_tb - free_query_tb) * query_cost_per_tb)

    # Total cost
    total_cost = storage_cost + query_cost + streaming_cost + egress_cost

    # Print results
    print(f"BigQuery Cost Breakdown for Project {project_id} (Last 30 Days):")
    print(f"  Storage Cost: ${storage_cost:.2f}")
    print(f"  Query Cost (On-Demand): ${query_cost:.2f} (Estimated: ${query_cost_estimate:.2f})")
    print(f"  Streaming Insert Cost: ${streaming_cost:.2f}")
    print(f"  Data Transfer (Egress) Cost: ${egress_cost:.2f}")
    print(f"  Total Cost: ${total_cost:.2f}")

    return {
        'storage_cost': storage_cost,
        'query_cost': query_cost,
        'streaming_cost': streaming_cost,
        'egress_cost': egress_cost,
        'total_cost': total_cost
    }

if __name__ == '__main__':
    project_id = 'your-project-id'  # Replace with your project ID
    billing_dataset = 'your-billing-dataset'  # Replace with your billing dataset
    billing_table = 'gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX'  # Replace with your billing table
    calculate_bigquery_costs(project_id, billing_dataset, billing_table)