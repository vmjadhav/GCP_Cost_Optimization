from ortools.linear_solver import pywraplp

def optimize_gcs_costs():
    # Create the solver (using SCIP for mixed-integer programming)
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver not created!")
        return

    # Sample data for objects (modify with your actual data)
    objects = [
        {'size_gb': 50, 'access_per_month': 2, 'storage_days': 30},  # Object 1
        {'size_gb': 100, 'access_per_month': 0.5, 'storage_days': 180},  # Object 2
        {'size_gb': 500, 'access_per_month': 0.1, 'storage_days': 365},  # Object 3
    ]
    num_objects = len(objects)

    # Storage classes and their properties
    storage_classes = [
        {'name': 'Standard', 'cost_per_gb': 0.023, 'retrieval_cost_per_gb': 0.0, 'min_days': 0},
        {'name': 'Nearline', 'cost_per_gb': 0.010, 'retrieval_cost_per_gb': 0.01, 'min_days': 30},
        {'name': 'Coldline', 'cost_per_gb': 0.004, 'retrieval_cost_per_gb': 0.02, 'min_days': 90},
        {'name': 'Archive', 'cost_per_gb': 0.0022, 'retrieval_cost_per_gb': 0.05, 'min_days': 365},
    ]
    num_classes = len(storage_classes)

    # Cost assumptions (modify as needed)
    egress_cost_per_gb = 0.12  # Network egress cost
    class_a_ops_cost = 0.05 / 10000  # Cost per Class A operation
    class_b_ops_cost = 0.004 / 10000  # Cost per Class B operation
    ops_per_access = 1  # Assume 1 Class B operation (GET) per access

    # Decision variables: x[i][j] = 1 if object i is assigned to storage class j, else 0
    x = {}
    for i in range(num_objects):
        for j in range(num_classes):
            x[i, j] = solver.BoolVar(f'x[{i}][{j}]')

    # Constraint: Each object must be assigned to exactly one storage class
    for i in range(num_objects):
        solver.Add(sum(x[i, j] for j in range(num_classes)) == 1)

    # Constraint: Respect minimum storage duration for Nearline, Coldline, Archive
    for i in range(num_objects):
        for j in range(num_classes):
            if storage_classes[j]['min_days'] > objects[i]['storage_days']:
                # If storage duration is less than minimum, prevent assignment
                solver.Add(x[i, j] == 0)

    # Objective: Minimize total cost (Storage + Retrieval + Egress + Operations)
    total_cost = 0

    for i in range(num_objects):
        for j in range(num_classes):
            # Storage cost
            storage_cost = objects[i]['size_gb'] * storage_classes[j]['cost_per_gb']
            # Retrieval cost (based on access frequency)
            retrieval_cost = objects[i]['size_gb'] * objects[i]['access_per_month'] * storage_classes[j]['retrieval_cost_per_gb']
            # Egress cost (assume all accesses involve egress)
            egress_cost = objects[i]['size_gb'] * objects[i]['access_per_month'] * egress_cost_per_gb
            # Operations cost (assume Class B operations for accesses)
            ops_cost = objects[i]['access_per_month'] * ops_per_access * class_b_ops_cost
            # Early deletion cost (if storage_days < min_days, already constrained to not select)
            total_cost += x[i, j] * (storage_cost + retrieval_cost + egress_cost + ops_cost)

    solver.Minimize(total_cost)

    # Solve the problem
    status = solver.Solve()

    # Output results
    if status == pywraplp.Solver.OPTIMAL:
        print(f'Optimal solution found with total cost: ${solver.Objective().Value():.2f}')
        for i in range(num_objects):
            for j in range(num_classes):
                if x[i, j].solution_value() > 0:
                    print(f"Object {i+1}: Assigned to {storage_classes[j]['name']}")
                    print(f"  Size: {objects[i]['size_gb']} GB, Accesses: {objects[i]['access_per_month']}/month")
                    print(f"  Storage Cost: ${objects[i]['size_gb'] * storage_classes[j]['cost_per_gb']:.2f}")
                    print(f"  Retrieval Cost: ${objects[i]['size_gb'] * objects[i]['access_per_month'] * storage_classes[j]['retrieval_cost_per_gb']:.2f}")
                    print(f"  Egress Cost: ${objects[i]['size_gb'] * objects[i]['access_per_month'] * egress_cost_per_gb:.2f}")
                    print(f"  Operations Cost: ${objects[i]['access_per_month'] * ops_per_access * class_b_ops_cost:.2f}")
    else:
        print('No optimal solution found.')

if __name__ == '__main__':
    optimize_gcs_costs()
