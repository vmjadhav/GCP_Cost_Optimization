from ortools.linear_solver import pywraplp

def optimize_gcs_storage():
    # Create the MIP solver
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver not created.")
        return

    # Problem data
    datasets = [
        {'size': 1000, 'access': 100, 'high_freq': True},  # Dataset 1
        {'size': 5000, 'access': 50, 'high_freq': False},  # Dataset 2
        {'size': 10000, 'access': 10, 'high_freq': False}  # Dataset 3
    ]
    # 20 + 100 + 200 = $320
    storage_classes = [
        {'name': 'Standard', 'storage_cost': 0.020, 'retrieval_cost': 0.0},  # $0.020/GB, $0/GB
        {'name': 'Nearline', 'storage_cost': 0.010, 'retrieval_cost': 0.01}, # $0.010/GB, $0.01/GB
        {'name': 'Coldline', 'storage_cost': 0.004, 'retrieval_cost': 0.02}, # $0.004/GB, $0.02/GB
        {'name': 'Archive', 'storage_cost': 0.0012, 'retrieval_cost': 0.05} # $0.0012/GB, $0.05/GB
    ]
    budget = 250.0  # $250/month
    num_datasets = len(datasets)
    num_classes = len(storage_classes)

    # Variables: x[i][j] = 1 if dataset i is in storage class j, 0 otherwise
    x = [[solver.BoolVar(f'x[{i}][{j}]') for j in range(num_classes)]
         for i in range(num_datasets)]
    
    # print("x :: ", x)
    # for i in range(num_datasets):
    #     for j in range(num_classes):
    #         print("X i j", x[{i}][{j}])


   
    # Constraints
    # 1. Each dataset is assigned to exactly one storage class
    for i in range(num_datasets):
        solver.Add(sum(x[i][j] for j in range(num_classes)) == 1)

    # 2. High-frequency datasets (Dataset 1) can only use Standard or Nearline
    for i in range(num_datasets):
        if datasets[i]['high_freq']:
            solver.Add(x[i][2] == 0)  # No Coldline
            solver.Add(x[i][3] == 0)  # No Archive

    # 3. Budget constraint
    total_cost = 0
    for i in range(num_datasets):
        for j in range(num_classes):
            storage_cost = datasets[i]['size'] * storage_classes[j]['storage_cost']
            retrieval_cost = datasets[i]['access'] * storage_classes[j]['retrieval_cost']
            total_cost += x[i][j] * (storage_cost + retrieval_cost)
    solver.Add(total_cost <= budget)

    # Objective: Minimize total cost
    solver.Minimize(total_cost)

    # Solve
    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        print(f'Optimal solution found. Total cost: ${solver.Objective().Value():.2f}/month')
        for i in range(num_datasets):
            for j in range(num_classes):
                if x[i][j].solution_value() > 0.5:
                    print(f"Dataset {i+1}: {storage_classes[j]['name']}, "
                          f"Storage cost: ${datasets[i]['size'] * storage_classes[j]['storage_cost']:.2f}, "
                          f"Retrieval cost: ${datasets[i]['access'] * storage_classes[j]['retrieval_cost']:.2f}")
    else:
        print('No optimal solution found.')

# Run the solver
optimize_gcs_storage()