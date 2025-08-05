from google.cloud import bigquery
from google.oauth2 import service_account
from config import SERVICE_ACCOUNT_KEY

# Create credentials object
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY)
client = bigquery.Client(credentials=credentials)

def get_query_demand():
    """
    Fetches the total amount of data processed in BigQuery queries for the last 30 days in tebibytes (TiB).

    The function runs a SQL query against the INFORMATION_SCHEMA.JOBS_BY_PROJECT view 
    scoped to the US region to sum the `total_bytes_processed` for all completed (`state = 'DONE'`) 
    query jobs executed in the past 30 days.

    Returns:
        float: Total data processed by queries in the last 30 days, expressed in tebibytes (TiB).
    
    Side effects:
        Prints the total TiB processed in last 30 days formatted to 4 decimal places.
    """

    query = """
    SELECT
    SUM(total_bytes_processed)/POWER(1024,4) AS total_tib_processed
    FROM
    `region-US`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
    WHERE
    creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    AND state = 'DONE'
    AND job_type = 'QUERY'
    """
    query_job = client.query(query)
    result = query_job.result()
    for row in result:
        query_demand = round(float(row.total_tib_processed), 2)
    print(f'#### Last 30 days TiB processed ::  {query_demand}')
    print('------------------------------------------------------------- ')
    return query_demand

#get_query_demand()