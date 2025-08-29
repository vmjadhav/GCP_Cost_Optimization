from google.cloud import bigquery
from google.oauth2 import service_account
from config import SERVICE_ACCOUNT_KEY

# Create credentials object
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY)
client = bigquery.Client(credentials=credentials)

def get_query_demand():
    """
    Retrieves the total amount of data processed by BigQuery jobs of type 'QUERY' for the
    current project over the last 30 days.

    This function queries the BigQuery `INFORMATION_SCHEMA.JOBS_BY_PROJECT` table to calculate
    the total bytes processed by completed query jobs within the past 30 days. The result is
    converted from bytes to tebibytes (TiB) and rounded to two decimal places. The function
    assumes a pre-initialized BigQuery client and prints the result before returning it.

    Returns:
        float: Total data processed in tebibytes (TiB), rounded to two decimal places.

    Raises:
        google.cloud.exceptions.GoogleCloudError: If the BigQuery query fails or the client
            encounters an API error.
        NameError: If the `client` object is not defined or initialized in the global scope.
        TypeError: If the query result cannot be processed due to unexpected data types.

    Example:
        >>> demand = get_query_demand()
        #### Last 30 days TiB processed ::  12.34
        -------------------------------------------------------------
        >>> print(demand)
        12.34

    Notes:
        - The function assumes the existence of a global `client` object, typically a
          `google.cloud.bigquery.Client` instance, authenticated and configured with the
          appropriate project ID.
        - The query targets the `region-US` region. Modify the query string if a different
          region is required.
        - Only jobs with `state = 'DONE'` and `job_type = 'QUERY'` are included in the
          calculation.
        - The result is printed to the console with a formatted message before being returned.
        - The conversion to tebibytes uses `POWER(1024, 4)` (1 TiB = 2^40 bytes).
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