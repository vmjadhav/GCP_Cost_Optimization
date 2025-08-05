from ortools.linear_solver import pywraplp

solver = pywraplp.Solver.CreateSolver('SCIP')

standard = solver.IntVar(0, 100, 'standard')
spot = solver.IntVar(0, 100, 'spot')
cud = solver.BoolVar('cud')  # Enable CUD?

# Auxiliary var for product standard * cud
standard_cud = solver.IntVar(0, 100, 'standard_cud')

# Constraints to linearize standard_cud = standard * cud
solver.Add(standard_cud <= standard)
solver.Add(standard_cud <= 100 * cud)
solver.Add(standard_cud >= standard - 100 * (1 - cud))
solver.Add(standard_cud >= 0)

# Constraints
solver.Add(standard + spot == 100)
solver.Add(spot <= 50)

# Cost terms
cost_standard = 0.04 * standard - 0.012 * standard_cud
cost_spot = 0.01 * spot

# Objective
objective = solver.Objective()
objective.SetCoefficient(standard, 0.04)
objective.SetCoefficient(standard_cud, -0.012)
objective.SetCoefficient(spot, 0.01)
objective.SetMinimization()

status = solver.Solve()

if status == pywraplp.Solver.OPTIMAL:
    print(f'Standard vCPUs: {standard.solution_value()}')
    print(f'Spot vCPUs: {spot.solution_value()}')
    print(f'CUD Enabled: {cud.solution_value()}')
    print(f'Total Cost: {solver.Objective().Value()} $/hour')
else:
    print("The solver did not find an optimal solution.")
