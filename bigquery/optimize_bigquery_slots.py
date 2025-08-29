# python -m agent.bigquery_cost_optimizer_agent

# Step 1 : Import the linear solver wrapper,
from ortools.linear_solver import pywraplp
from .bigquery_cost_calculator import calculate_detailed_costs
from data_utility import dummy_bigquery_mixed_data, dummy_bigquery_6mean_4std_data
from config import SLOTS_PER_TIB, MAX_RESERVED_SLOTS
import json
import pandas as pd


def optimize_slots(data_df: pd.DataFrame):
    """
    Optimizes BigQuery slot allocation to minimize costs using a mixed-integer programming solver.

    This function takes BigQuery job data and uses a MIP solver (CBC) to determine the optimal
    number of reserved slots and on-demand tebibytes (TiB) to minimize total costs, given a maximum
    number of reserved slots. It first calculates current costs using the `calculate_detailed_costs`
    function with `slot_type` to split on-demand and flat-rate jobs. Then, it optimizes by balancing
    reserved slot costs (at $0.04 per slot-hour over a 30-day period) and on-demand costs (at $6.25
    per TiB). The optimized allocation is used to recalculate costs, which are printed for comparison.

    Args:
        data_df (pd.DataFrame): A pandas DataFrame containing BigQuery job data with the following
            required columns:
                - end_time_epoch (int64): Job end time in Unix milliseconds.
                - start_time_epoch (int64): Job start time in Unix milliseconds.
                - total_slot_ms (int64): Total slot-milliseconds consumed by the job.
                - total_bytes_processed (int64): Bytes processed by the job.
                - slot_type (str): 'On-Demand' or 'Reserved' to indicate job type.
        total_reserved_slots (int, optional): Maximum number of reserved slots available.
            Must be non-negative. Defaults to 50.

    Returns:
        Tuple[float, float]: A tuple containing:
            - reserved (float): Number of reserved slots recommended by the solver.
            - on_demand_tib_processed (float): Number of on-demand TiB to process.

    Raises:
        KeyError: If required columns (`end_time_epoch`, `start_time_epoch`, `total_slot_ms`,
            `total_bytes_processed`, `slot_type`) are missing from `data_df`.
        ValueError: If `total_reserved_slots` is negative or if `data_df` is empty.
        ImportError: If the `ortools` library is not installed.
        RuntimeError: If the solver fails to find an optimal solution.

    Example:
        >>> import pandas as pd
        >>> data = pd.DataFrame({
        ...     'slot_type': ['On-Demand', 'Reserved'],
        ...     'start_time_epoch': [1696161600000, 1696161600000],
        ...     'end_time_epoch': [1696181544000, 1696181544000],
        ...     'total_slot_ms': [1994400000, 1994400000],
        ...     'total_bytes_processed': [7.5 * 1024**4, 7.5 * 1024**4]
        ... })
        >>> reserved, on_demand = optimize_slots(data, total_reserved_slots=100)
        #### Reserved Slots ::  100
        #### BigQuery Cost before optimization ::
        -------------------------------------------------------------
        costs_and_metrics:  {
            "on_demand_price_per_tib": 6.25,
            "on_demand_cost": 40.62,
            "on_demand_slots": 720.0,
            "on_demand_hours": 2.77,
            "on_demand_tib_processed": 7.5,
            "flat_rate_price_per_slot_hour": 0.04,
            "flat_rate_cost": 39.89,
            "flat_rate_slots": 720.0,
            "flat_rate_hours": 2.77,
            "flat_rate_tib_processed": 7.5,
            "total_cost": 80.51
        }
        #### Reserved Slots: 15.0, On-Demand TiB: 0.0
        #### BigQuery Cost After optimization ::
        -------------------------------------------------------------
        costs_and_metrics:  {
            "on_demand_price_per_tib": 6.25,
            "on_demand_cost": 0.0,
            "on_demand_slots": 0.0,
            "on_demand_hours": 0.55,
            "on_demand_tib_processed": 0.0,
            "flat_rate_price_per_slot_hour": 0.04,
            "flat_rate_cost": 432.0,
            "flat_rate_slots": 15.0,
            "flat_rate_hours": 4.99,
            "flat_rate_tib_processed": 15.0,
            "total_cost": 432.0
        }
        >>> print(reserved, on_demand)
        15.0 0.0

    Notes:
        - The function assumes 10 slots are needed per TiB processed (`slots_per_tib = 10`).
        - Reserved slot costs are calculated over a 30-day period (720 hours) for monthly cost
          estimation, which may be adjusted based on workload duration (e.g., 5.54 hours).
        - The solver minimizes total cost, balancing reserved slot costs and on-demand costs.
        - The function calls `calculate_detailed_costs` twice: once to assess current costs using
          `slot_type`, and once with optimized `reserved_slots` and `on_demand_tib_processed`.
        - If the reserved output is zero, verify that `total_tib_processed` is non-zero and
          `slot_type` includes 'Reserved' jobs.
        - The function assumes the `calculate_detailed_costs` function returns metrics including
          `on_demand_tib_processed`, `flat_rate_tib_processed`, `flat_rate_price_per_slot_hour`,
          and `on_demand_price_per_tib`.
    """

    costs_and_metrics = calculate_detailed_costs(data_df, None, None)

    print('#### BigQuery Cost before optimization :: ')
    print('------------------------------------------------------------- ')
    print(f"costs_and_metrics: ", json.dumps(costs_and_metrics, indent=4))
    

    # Step 2 : declare the MIP solver
    solver = pywraplp.Solver.CreateSolver('CBC')


    # Step 3 : define the variables
    on_demand_tib = solver.NumVar(0, solver.infinity(), 'on_demand_tib')
    reserved_slots = solver.IntVar(0, MAX_RESERVED_SLOTS, 'reserved_slots')     # Number of flat-rate slots reserved

    tb_processed = costs_and_metrics['on_demand_tib_processed'] + costs_and_metrics['flat_rate_tib_processed']    # Total TB processed
    slots_per_tib = SLOTS_PER_TIB  # Approx. slots needed per TiB processed


    # Costs
    slot_cost = float(costs_and_metrics['flat_rate_price_per_slot_hour'])  # $/slot-hour
    on_demand_cost = costs_and_metrics['on_demand_price_per_tib']  # $/TiB


    # Step 4 : define the constraints
    # Constraint: Meet query demand
    solver.Add(reserved_slots * slots_per_tib + on_demand_tib >= tb_processed)

    mean_tb = data_df['total_bytes_processed'].mean() / (1024**4)
    std_tb = data_df['total_bytes_processed'].std() / (1024**4)

    solver.Add(reserved_slots * slots_per_tib >= mean_tb)
    solver.Add(on_demand_tib >= std_tb)


    # Step 5: define the objective Objective: Minimize cost
    objective = solver.Objective()
    objective.SetCoefficient(reserved_slots, slot_cost * 5.24)  # Monthly cost
    objective.SetCoefficient(on_demand_tib, on_demand_cost)
    objective.SetMinimization()


    # Step 6 : call the MIP solver
    solver.Solve()


    # Step 7: return the solution
    reserved = reserved_slots.solution_value()
    on_demand_tib_processed = on_demand_tib.solution_value()
    print(f"#### Reserved Slots: {reserved}, On-Demand TiB: {on_demand_tib_processed}")
    
    print('#### BigQuery Cost After optimization :: ')
    print('------------------------------------------------------------- ')
    costs_with_reserved_slots = calculate_detailed_costs(data_df, reserved, on_demand_tib_processed)
    print(f"costs_and_metrics: ", json.dumps(costs_with_reserved_slots, indent=4))

    return reserved, on_demand_tib_processed


optimize_slots(dummy_bigquery_mixed_data)
optimize_slots(dummy_bigquery_6mean_4std_data)
# python -m bigquery.optimize_bigquery_slots 