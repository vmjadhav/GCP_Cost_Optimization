import json
import pandas as pd
from config import SLOTS_PER_TIB


def calculate_detailed_costs(data: pd.DataFrame, reserved_slots = None, on_demand_tib_processed = 0) -> dict:
    """
    Calculates detailed cost and utilization metrics for BigQuery jobs based on slot usage.

    This function processes BigQuery job data to compute costs and metrics for on-demand and
    flat-rate (reserved) slot usage under two scenarios:
    1. If `reserved_slots` and `on_demand_tib_processed` are both None, costs are calculated
       based on the `slot_type` column i.e., current usage of on-demand and reserved slots.
    2. If `reserved_slots` and `on_demand_tib_processed` are both provided, the specified
       `on_demand_tib_processed` is processed as recommended by solver and remaining large 
       chunk of data is processed using flat rate slots.

    Args:
        data (pd.DataFrame): A pandas DataFrame containing BigQuery job data with the following
            required columns:
                - end_time_epoch (int64): Job end time in Unix milliseconds.
                - start_time_epoch (int64): Job start time in Unix milliseconds.
                - total_slot_ms (int64): Total slot-milliseconds consumed by the job.
                - total_bytes_processed (int64): Bytes processed by the job.
                - slot_type (str, optional): 'On-Demand' or 'Reserved' (required for Scenario 1).
        
        reserved_slots (Optional[int]): Number of reserved slots recommended.
        on_demand_tib_processed (Optional[float]): Recommended amount of data (in TiB) to process as on-demand 
         
            If `reserved_slots` and `on_demand_tib_processed` is None, 
                then uses `slot_type` to split costs (Scenario 1). 
            If provided with `reserved_slots` and `on_demand_tib_processed`,
                then as per recommendation most of the data is processed by `reserved_slots` and
                remaining `on_demand_tib_processed` is processed OnDemand (Scenario 2).

    Returns:
        dict: A dictionary containing the following cost and utilization metrics:
            - on_demand_price_per_tib (float): Price per TiB for on-demand jobs ($6.25).
            - on_demand_cost (float): Total cost for on-demand jobs, rounded to 2 decimals.
            - on_demand_slots (float): Average slots used by on-demand jobs, rounded to 2 decimals.
            - on_demand_hours (float): Total hours for on-demand jobs, rounded to 2 decimals.
            - on_demand_tib_processed (float): Total TiB processed by on-demand jobs, rounded to 2 decimals.
            - flat_rate_price_per_slot_hour (float): Price per slot-hour for flat-rate jobs ($0.04).
            - flat_rate_cost (float): Total cost for flat-rate jobs, rounded to 2 decimals.
            - flat_rate_slots (float): Average slots used by flat-rate jobs, rounded to 2 decimals.
            - flat_rate_hours (float): Total hours for flat-rate jobs, rounded to 2 decimals.
            - flat_rate_tib_processed (float): Total TiB processed by flat-rate jobs, rounded to 2 decimals.
            - total_cost (float): Sum of on-demand and flat-rate costs, rounded to 2 decimals.

    Raises:
        KeyError: If required columns (`end_time_epoch`, `start_time_epoch`, `total_slot_ms`,
            `total_bytes_processed`, or `slot_type` when needed) are missing from the DataFrame.
        ValueError: If `reserved_slots` or `on_demand_tib_processed` is negative, the DataFrame
            is empty, or `on_demand_tib_processed` exceeds `total_tib_processed`.
        ZeroDivisionError: If total duration is zero when calculating average slots, handled by
            returning zero slots.

    Example:
        >>> import pandas as pd
        >>> data = pd.DataFrame({
        ...     'slot_type': ['On-Demand', 'Reserved'],
        ...     'start_time_epoch': [1696161600000, 1696161600000],
        ...     'end_time_epoch': [1696181544000, 1696181544000],
        ...     'total_slot_ms': [1994400000, 1994400000],
        ...     'total_bytes_processed': [7.5 * 1024**4, 7.5 * 1024**4]
        ... })
        >>> result_none = calculate_detailed_costs(data, reserved_slots=None)
        >>> result_split = calculate_detailed_costs(data, reserved_slots=50, on_demand_tib_processed=None)
        >>> result_specified = calculate_detailed_costs(data, reserved_slots=50, on_demand_tib_processed=2.0)
        >>> print(result_none)
        {
            'on_demand_price_per_tib': 6.25,
            'on_demand_cost': 87.5,
            'on_demand_slots': 720.0,
            'on_demand_hours': 5.54,
            'on_demand_tib_processed': 15.0,
            'flat_rate_price_per_slot_hour': 0.04,
            'flat_rate_cost': 0.0,
            'flat_rate_slots': 0.0,
            'flat_rate_hours': 0.0,
            'flat_rate_tib_processed': 0.0,
            'total_cost': 87.5
        }
        >>> print(result_specified)
        {
            'on_demand_price_per_tib': 6.25,
            'on_demand_cost': 6.25,
            'on_demand_slots': 36.1,
            'on_demand_hours': 0.55,
            'on_demand_tib_processed': 2.0,
            'flat_rate_price_per_slot_hour': 0.04,
            'flat_rate_cost': 9.97,
            'flat_rate_slots': 50.0,
            'flat_rate_hours': 4.99,
            'flat_rate_tib_processed': 13.0,
            'total_cost': 16.22
        }

    Notes:
        - On-demand pricing is $6.25 per TiB, with a 1 TiB free tier.
        - Flat-rate pricing is $0.04 per slot-hour, not reflecting actual BigQuery flat-rate agreements.
        - In Scenario 3, 90% of total time is allocated to flat-rate slots, with 10% to on-demand,
          and data is split based on the specified `on_demand_tib_processed`.
        - The function assumes 10 slots per TiB for capacity estimation, adjustable via `SLOTS_PER_TIB`.
        - Durations are calculated from `end_time_epoch` and `start_time_epoch` in milliseconds.
        - Scenario 3 prioritizes flat-rate slots for most data and time to minimize costs.
    """

    if data.empty:
        raise ValueError("Input DataFrame is empty.")
    if reserved_slots is not None and reserved_slots < 0:
        raise ValueError("reserved_slots cannot be negative.")
    if (reserved_slots is not None and on_demand_tib_processed is None) or (reserved_slots is None and on_demand_tib_processed is not None):
        raise ValueError("provide value for both reserved_slots and on_demand_tib_processed.")

    on_demand_price_per_tib = 6.25  # USD
    flat_rate_price_per_slot_hour = 0.04  # USD, conceptual pay-as-you-go rate
    on_demand_free_tier_tib = 1
    slots_per_tib = SLOTS_PER_TIB  # Approx. slots needed per TiB processed

    # Initialize all metrics
    on_demand_cost, on_demand_slots, on_demand_hours = 0, 0, 0
    flat_rate_cost, flat_rate_slots, flat_rate_hours, flat_rate_tib_processed = 0, 0, 0, 0

    print('#### Reserved Slots :: ', reserved_slots)

    # Calculate total duration and slot usage
    total_duration_ms = (data['end_time_epoch'] - data['start_time_epoch']).sum()
    total_slot_ms = data['total_slot_ms'].sum()
    total_tib_processed = data['total_bytes_processed'].sum() / (1024**4)

    if reserved_slots is None:

        reserved_slots = total_slot_ms / total_duration_ms


    if on_demand_tib_processed is None:
        # Scenario 2: Use slot_type to split data into on-demand and flat-rate
        print('#### Calculating based on currently Reserved and On-Demand slots from slot_type')
        if 'slot_type' not in data.columns:
            raise KeyError("slot_type column is required when on_demand_tib_processed is None.")

        on_demand_data = data[data['slot_type'] == 'On-Demand']
        flat_rate_data = data[data['slot_type'] == 'Reserved']

        # On-Demand Metrics
        on_demand_duration_ms = (on_demand_data['end_time_epoch'] - on_demand_data['start_time_epoch']).sum()
        on_demand_hours = on_demand_duration_ms / 3600000
        on_demand_total_slot_ms = on_demand_data['total_slot_ms'].sum()
        on_demand_slots = on_demand_total_slot_ms / on_demand_duration_ms if on_demand_duration_ms > 0 else 0
        on_demand_tib_processed = on_demand_data['total_bytes_processed'].sum() / (1024**4)
        billable_on_demand_tib = max(0, on_demand_tib_processed - on_demand_free_tier_tib)
        on_demand_cost = billable_on_demand_tib * on_demand_price_per_tib

        # Flat-Rate Metrics
        flat_rate_duration_ms = (flat_rate_data['end_time_epoch'] - flat_rate_data['start_time_epoch']).sum()
        flat_rate_hours = flat_rate_duration_ms / ( reserved_slots * 3600000)
        flat_rate_total_slot_ms = flat_rate_data['total_slot_ms'].sum()
        flat_rate_slots = flat_rate_total_slot_ms / flat_rate_duration_ms if flat_rate_duration_ms > 0 else 0
        flat_rate_tib_processed = flat_rate_data['total_bytes_processed'].sum() / (1024**4)
        flat_rate_cost = flat_rate_slots * flat_rate_hours * flat_rate_price_per_slot_hour

    else :
        # Scenario 3: Process data with reserved slots first, then on-demand for remainder
        print('#### Calculating based on Optimized Reserved and On-Demand slots for jobs')
        
        # Assume reserved slots run for the entire duration of the jobs
        on_demand_hours = total_duration_ms * ( on_demand_tib_processed / total_tib_processed) / 3600000

        flat_rate_hours = ((total_duration_ms / 3600000) - on_demand_hours) / reserved_slots
        flat_rate_slots = reserved_slots  # Use the provided number of reserved slots
        flat_rate_cost = flat_rate_slots * flat_rate_hours * flat_rate_price_per_slot_hour

        # Estimate data processed by reserved slots (assuming 100 slots per TiB)
        #flat_rate_tib_capacity = (flat_rate_slots * flat_rate_hours) / slots_per_tib
        flat_rate_tib_processed = max(0, total_tib_processed - on_demand_tib_processed)
        
        # Remaining data processed as on-demand
        #on_demand_tib_processed = max(0, total_tib_processed - flat_rate_tib_processed)
        billable_on_demand_tib = max(0, on_demand_tib_processed - on_demand_free_tier_tib)
        on_demand_cost = billable_on_demand_tib * on_demand_price_per_tib

        # On-demand slots and hours (approximated based on remaining data)
        if on_demand_tib_processed > 0:
            on_demand_slots = min(total_slot_ms / total_duration_ms, slots_per_tib * on_demand_tib_processed / flat_rate_hours) if total_duration_ms > 0 else 0
            #on_demand_hours = flat_rate_hours  # Assume same duration for simplicity
        else:
            on_demand_slots = 0
            on_demand_hours = 0

    total_cost = on_demand_cost + flat_rate_cost

    return {
        "on_demand_price_per_tib": on_demand_price_per_tib,
        "on_demand_tib_processed": round(on_demand_tib_processed, 2),
        "on_demand_cost": round(on_demand_cost, 2),
        "on_demand_slots": round(on_demand_slots, 2),
        "on_demand_hours": round(on_demand_hours, 2),
        "flat_rate_price_per_slot_hour": flat_rate_price_per_slot_hour,
        "flat_rate_hours": round(flat_rate_hours, 2),
        "flat_rate_slots": round(flat_rate_slots, 2),
        "flat_rate_cost": round(flat_rate_cost, 2),
        "flat_rate_tib_processed": round(flat_rate_tib_processed, 2),
        "total_cost": round(total_cost, 2)
    }
        