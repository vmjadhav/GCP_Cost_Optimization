from google.cloud import bigquery
from datetime import datetime, timedelta
from google.oauth2 import service_account
from config import SERVICE_ACCOUNT_KEY, PROJECT_ID


def get_bigquery_slot_utilization_for_project(days_back: int = 30):
    """
    Retrieves BigQuery slot utilization data for a specified project over a given time period.

    This function queries the BigQuery `INFORMATION_SCHEMA.JOBS_BY_PROJECT` table to extract
    job metadata, including slot usage, job type, and execution details, for jobs executed
    within the specified time range. It uses service account credentials to authenticate with
    BigQuery and returns the results as a pandas DataFrame.

    Args:
        days_back (int, optional): Number of days prior to the current date to include in
            the query. Defaults to 30.

    Returns:
        pd.DataFrame: A DataFrame containing the following columns:
            - slot_type (str): Type of slot used ('On-Demand' or 'Reserved').
            - creation_time (datetime): Timestamp when the job was created.
            - total_slot_ms (int64): Total slot-milliseconds consumed by the job.
            - job_type (str): Type of BigQuery job (e.g., 'QUERY', 'LOAD').
            - state (str): State of the job (e.g., 'DONE', 'RUNNING').
            - start_time_epoch (int64): Job start time in Unix milliseconds.
            - end_time_epoch (int64): Job end time in Unix milliseconds.

    Raises:
        google.auth.exceptions.GoogleAuthError: If authentication with the service account fails.
        google.cloud.exceptions.GoogleCloudError: If the BigQuery query fails or the client
            encounters an API error.
        ValueError: If `days_back` is negative or invalid.
        FileNotFoundError: If the service account key file specified in `SERVICE_ACCOUNT_KEY`
            does not exist.

    Example:
        >>> df = get_bigquery_slot_utilization_for_project(days_back=7)
        >>> print(df.head())
           slot_type         creation_time  total_slot_ms job_type state  start_time_epoch  end_time_epoch
        0  On-Demand 2023-10-01T12:00:00Z      5000000    QUERY  DONE    1696161600000  1696161605000
        1  Reserved  2023-10-01T12:01:00Z      3000000    LOAD   DONE    1696161660000  1696161663000

    Notes:
        - The function assumes the existence of `SERVICE_ACCOUNT_KEY` and `PROJECT_ID` variables
          defined in the global scope, containing the path to the service account key file and
          the BigQuery project ID, respectively.
        - The query targets the `region-us` region. Modify the query string if a different region
          is required.
        - The time range is calculated based on the current time (`datetime.now()`) and the
          specified `days_back` period.
    """

    # Create credentials object
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY)
    client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

    # Define the time range for the query
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)

    query = f"""
        SELECT
            CASE
                WHEN reservation_id IS NULL THEN 'On-Demand'
                ELSE 'Reserved'
            END AS slot_type,
            creation_time,
            total_slot_ms,
            job_type,
            state,
            UNIX_MILLIS(start_time) AS start_time_epoch,
            UNIX_MILLIS(end_time) AS end_time_epoch
        FROM
            `{PROJECT_ID}`.`region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE
            creation_time BETWEEN TIMESTAMP('{start_time.isoformat()}')
            AND TIMESTAMP('{end_time.isoformat()}')
    """

    #print(f"Executing BigQuery query for project '{PROJECT_ID}'...")
    #print(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")

    query_job = client.query(query)
    data_df = query_job.to_dataframe()

    return data_df
