from ortools.linear_solver import pywraplp

def schedule_queries():
    # Create the MIP solver
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver not created.")
        return

    # Problem data
    num_queries = 3
    time_slots = 9  # 9 AM to 6 PM (hourly slots)
    data_scanned = [0.5, 2.0, 1.0]  # TB scanned by queries Q1, Q2, Q3
    slots_required = [20, 50, 30]  # Slots for Q1, Q2, Q3 (flat-rate)
    runtimes = [1, 2, 1]  # Hours required by Q1, Q2, Q3
    deadlines = [6, 8, 9]  # Deadlines in time slots (3 PM, 5 PM, 6 PM)
    on_demand_cost = 5.0  # $5/TB
    flat_rate_cost = 4.0  # $4/hour for 100 slots
    max_slots = 100  # Flat-rate slot capacity

    # Variables
    # x[i][t]: 1 if query i starts at time t, 0 otherwise
    # x[i][t]: Binary variable indicating if query i starts at time t.
    x = [[solver.BoolVar(f'x[{i}][{t}]') for t in range(time_slots)] for i in range(num_queries)]
    # y[i]: 1 if query i uses on-demand, 0 if flat-rate
    # y[i]: Binary variable indicating the pricing method for query i (1 = on-demand, 0 = flat-rate).
    y = [solver.BoolVar(f'y[{i}]') for i in range(num_queries)]
    # s[i][t]: Slots used by query i at time t (flat-rate only)
    # s[i][t]: Continuous variable for slots used by query i at time t under flat-rate.
    s = [[solver.NumVar(0, max_slots, f's[{i}][{t}]') for t in range(time_slots)] for i in range(num_queries)]

    # Constraints
    # 1. Each query runs exactly once
    for i in range(num_queries):
        solver.Add(sum(x[i][t] for t in range(time_slots)) == 1)

    # 2. Respect deadlines and runtime
    for i in range(num_queries):
        for t in range(time_slots):
            if t + runtimes[i] > deadlines[i]:
                solver.Add(x[i][t] == 0)  # Cannot start if it exceeds deadline

    # 3. Slot usage for flat-rate queries
    for i in range(num_queries):
        for t in range(time_slots):
            # If query i starts at t and uses flat-rate (y[i] = 0), assign slots
            solver.Add(s[i][t] <= slots_required[i] * x[i][t])
            solver.Add(s[i][t] <= max_slots * (1 - y[i]))
            # For runtime > 1, assign slots to subsequent time slots
            for k in range(1, runtimes[i]):
                if t + k < time_slots:
                    # For runtimes longer than 1 hour, also assigns slots at subsequent time slots.
                    solver.Add(s[i][t + k] <= slots_required[i] * x[i][t])
                    # Ensures slots used cannot exceed maximum available flat-rate slots.
                    solver.Add(s[i][t + k] <= max_slots * (1 - y[i]))

    # 4. Total slots per time slot <= max_slots
    for t in range(time_slots):
        solver.Add(sum(s[i][t] for i in range(num_queries)) <= max_slots)

    # Objective: Minimize total cost
    # On-demand cost + flat-rate cost (flat-rate cost is fixed at $4/hour × 9 hours)
    on_demand_cost_expr = sum(y[i] * data_scanned[i] * on_demand_cost for i in range(num_queries))
    total_cost = on_demand_cost_expr + flat_rate_cost * time_slots
    solver.Minimize(total_cost)

    # Solve
    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        print(f'Optimal solution found. Total cost: ${solver.Objective().Value():.2f}')
        for i in range(num_queries):
            for t in range(time_slots):
                if x[i][t].solution_value() > 0.5:
                    pricing = 'On-demand' if y[i].solution_value() > 0.5 else 'Flat-rate'
                    print(f'Query {i+1}: Start at {9+t} AM, Pricing: {pricing}, '
                          f'Slots: {s[i][t].solution_value() if not y[i].solution_value() else 0}')
    else:
        print('No optimal solution found.')

# Run the solver
schedule_queries()