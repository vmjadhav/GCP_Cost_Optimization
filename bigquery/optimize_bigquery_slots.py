# python -m agent.bigquery_cost_optimizer_agent

# Step 1 : Import the linear solver wrapper,
from ortools.linear_solver import pywraplp
from .bigquery_byte_scanned import get_query_demand
from .bigquery_cost_calculator import calculate_bigquery_cost

def optimize_slots(query_demand: float, max_slots: int=50):
    """
    Optimize the allocation between reserved BigQuery slots and on-demand bytes processed to minimize cost.

    This function formulates and solves a Mixed-Integer Programming (MIP) problem to determine the optimal
    number of reserved slots to purchase (`reserved_slots`) and the remaining query demand to process on-demand (`on_demand_tib`),
    so that the total query demand (in tebibytes) is met at minimum cost.

    The cost model includes:
    - Flat-rate pricing cost based on the number of reserved slots and monthly slot-hour cost.
    - On-demand pricing cost based on the amount of data processed outside reserved slots.

    Args:
        query_demand (float): Total BigQuery query demand expressed in tebibytes (TiB) of processed data.
        max_slots (int, optional): Maximum number of reserved slots allowed in the optimization. Default is 50.

    Returns:
        tuple:
            - reserved_slots (float): The optimized number of reserved slots to allocate (integer value).
            - on_demand_tib (float): The optimized amount of data (TiB) to process using on-demand slots.

    Notes:
        - Assumes approximately 100 slots are needed to process 1 TiB of data.
        - Assumes monthly usage duration of 24 * 30 hours for slot cost calculation.
        - Uses CBC solver from Google OR-Tools for Mixed-Integer Programming.
        - The region is hardcoded to 'us' for pricing purposes; adjust as necessary for other regions.
        - The cost parameters (`flat_rate_slot_hourly_cost`, `on_demand_cost_per_tb`) are obtained
          from a `calculate_bigquery_cost` helper function, which must be defined separately.

    Raises:
        RuntimeError: If the solver fails to find an optimal solution.
    """

    # Step 2 : declare the MIP solver
    solver = pywraplp.Solver.CreateSolver('CBC')
    # Step 3 : define the variables
    on_demand_tib = solver.NumVar(0, solver.infinity(), 'on_demand_tib')
    region = 'us'                  # The region your BigQuery datasets reside in
    tb_processed = query_demand    # Total TB processed in on-demand pricing
    reserved_slots = solver.IntVar(0, max_slots, 'reserved_slots')     # Number of flat-rate slots reserved
    hours_per_month = 24 * 30      # Assuming reserved slots are used all month

    cost_details = calculate_bigquery_cost(region, tb_processed, reserved_slots, hours_per_month)

    # Costs
    slot_cost = float(cost_details['flat_rate_slot_hourly_cost'])  # $/slot-hour
    on_demand_cost = cost_details['on_demand_cost_per_tb']  # $/TiB
    slots_per_tib = 100  # Approx. slots needed per TiB processed
    # Step 4 : define the constraints
    # Constraint: Meet query demand
    solver.Add(reserved_slots * slots_per_tib + on_demand_tib >= query_demand)
    # Step 5: define the objective Objective: Minimize cost
    objective = solver.Objective()
    objective.SetCoefficient(reserved_slots, slot_cost * 24 * 30)  # Monthly cost
    objective.SetCoefficient(on_demand_tib, on_demand_cost)
    objective.SetMinimization()
    # Step 6 : call the MIP solver
    solver.Solve()
    # Step 7: return the solution
    reserved = reserved_slots.solution_value()
    on_demand = on_demand_tib.solution_value()
    print(f"#### Reserved Slots: {reserved}, On-Demand TiB: {on_demand}")
    return reserved, on_demand

# Example usage
#query_demand = get_query_demand() #500  # TiB/month
#query_demand = round(float(get_query_demand()), 2)

#print('query_demand :: ', query_demand)
#reserved, on_demand = optimize_slots(query_demand)
#print(f"Reserved Slots: {reserved}, On-Demand TiB: {on_demand}")

# Current Cloud Spend ::
# Cost per slot per hour - $0.04 
# reserved_slots, slot_cost * 24 * 30
# 0.04 * 24 * 30 - per slot = 28.8
# reserved_slots - 28.8 * 2000 = $57,600

# Project Optimized cloud spend ::
# 0.04 * 24 * 30 - per slot = 28.8
# reserved_slots - 28.8 * 5 = $144