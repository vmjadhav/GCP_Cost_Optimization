from google.cloud import bigquery
from datetime import datetime, timedelta
from google.oauth2 import service_account
from config import SERVICE_ACCOUNT_KEY, PROJECT_ID
import json

def get_bigquery_slot_utilization_for_project(days_back: int = 30):
    """
    Retrieves and aggregates BigQuery slot utilization data for a given project
    by querying INFORMATION_SCHEMA.JOBS_BY_PROJECT.

    Args:
        days_back (int): The number of days back from now to retrieve job data.

    Returns:
        dict: A dictionary containing aggregated slot usage data (e.g., total_slot_ms,
              total_jobs) or an empty dictionary if no data is found.
    """

    # Create credentials object
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY)
    client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

    # Define the time range for the query
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)

    query = f"""
    SELECT
        creation_time,
        total_slot_ms,
        job_type,
        state
    FROM
        `{PROJECT_ID}`.`region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
    WHERE
        creation_time BETWEEN TIMESTAMP('{start_time.isoformat()}')
        AND TIMESTAMP('{end_time.isoformat()}')
    """

    #print(f"Executing BigQuery query for project '{PROJECT_ID}'...")
    #print(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")

    try:
        query_job = client.query(query)
        rows = list(query_job.result())  # Waits for the query to complete

        total_slot_ms_sum = 0
        successful_jobs_count = 0
        failed_jobs_count = 0
        total_jobs_count = 0

        for row in rows:
            total_jobs_count += 1
            if row.state == 'DONE' and row.job_type == 'QUERY':
                ms = 0
                if row.total_slot_ms is not None:
                    ms = row.total_slot_ms 
                total_slot_ms_sum += ms
                successful_jobs_count += 1
            elif row.state == 'DONE' and row.job_type != 'QUERY':
                # Consider other job types if relevant for your "utilization" definition
                pass
            elif row.state == 'DONE' and row.total_slot_ms is None:
                # Some jobs might not consume slots (e.g., DDL, metadata queries)
                pass
            elif row.state == 'FAILED':
                failed_jobs_count += 1

        # Calculate total duration in milliseconds for the period
        # period_ms = (end_time - start_time).total_seconds() * 1000

        # Note: True "slot utilization" requires knowing your provisioned slots.
        # This example provides the *consumed* slot-milliseconds.
        # To calculate a percentage, you'd divide `total_slot_ms_sum` by
        # (`available_slots` * `period_ms`).


        results = {
            "project_id": PROJECT_ID,
            #"start_time": start_time.isoformat(),
            #"end_time": end_time.isoformat(),
            #"total_queried_jobs": total_jobs_count,
            #"successful_query_jobs": successful_jobs_count,
            #"failed_jobs": failed_jobs_count,
            #"total_slot_ms_consumed": total_slot_ms_sum,
            #"analysis_period_ms": period_ms,
            "total_slot_hours_consumed":  round(float(total_slot_ms_sum / (1000 * 60 * 60)), 2)
            # Add more calculations as needed, e.g., average slots used
            # average_slots_per_second = total_slot_ms_sum / period_ms if period_ms > 0 else 0
        }
        print('#### Slot Utilization Result :: ', json.dumps(results, indent=4))
        print('------------------------------------------------------------- ')
        return results

    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

"""
if __name__ == "__main__":
    # Replace with your actual project ID
    YOUR_PROJECT_ID = "cost-optimization-467817"

    # Set the number of days back to analyze
    DAYS_TO_ANALYZE = 7

    slot_data = get_bigquery_slot_utilization_for_project(30)

    if slot_data:
        print("\n--- BigQuery Slot Utilization Report ---")
        for key, value in slot_data.items():
            print(f"{key}: {value}")

        total_slot_hours_consumed = slot_data.get("total_slot_ms_consumed", 0) / (1000 * 60 * 60)
        print(f"Total Slot-Hours Consumed: {total_slot_hours_consumed:.2f} hours")

         # --- NEW CALCULATION ---
        total_slot_ms_consumed = slot_data.get("total_slot_ms_consumed", 0)
        analysis_period_ms = slot_data.get("analysis_period_ms", 0)

        if analysis_period_ms > 0:
            average_slots_consumed = total_slot_ms_consumed / analysis_period_ms
            print(f"Average Slots Consumed: {average_slots_consumed} slots")
        else:
            print("Cannot calculate average slots consumed (analysis period is zero).")


        # Example of how you *would* calculate utilization if you knew your reservation slots
        # For this, you would need to get your reservation assignments, e.g., using BigQuery Reservations API.
        # Let's assume you have 1000 baseline slots for the entire period.
        # This is a hypothetical example and needs actual reservation data for accuracy.
        # assumed_total_available_slots = 1000
        # analysis_period_seconds = slot_data.get("analysis_period_ms", 0) / 1000
        # max_possible_slot_seconds = assumed_total_available_slots * analysis_period_seconds
        #
        # if max_possible_slot_seconds > 0:
        #     utilization_percentage = (total_slot_ms_consumed / (max_possible_slot_seconds * 1000)) * 100
        #     print(f"Hypothetical Utilization (assuming {assumed_total_available_slots} slots): {utilization_percentage:.2f}%")
        # else:
        #     print("Cannot calculate hypothetical utilization (period or slots invalid).")

    else:
        print("Failed to retrieve slot utilization data.")
"""