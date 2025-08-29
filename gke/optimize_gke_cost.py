from ortools.linear_solver import pywraplp
from datetime import datetime, timedelta

# Configuration
PROJECT_ID = "your-project-id"
CLUSTER_HOURS = 730  # 30 days * ~24.33 hours/day
FREE_TIER_CREDIT = 74.40  # $74.40/month free tier for one zonal cluster
BIG_M = 1_000_000  # Large constant for big-M constraints

# Cost drivers (based on provided table, us-central1 pricing)
COST_DRIVERS = {
    "management_fee": 0.10,  # $0.10/hour per cluster
    "machine_types": {
        "n1-standard-2": {"cost_per_hour": 0.068 * 2, "vcpu": 2, "memory": 7.5},  # 2 vCPUs, 7.5 GB
        "e2-standard-2": {"cost_per_hour": 0.057 * 2, "vcpu": 2, "memory": 8.0},  # 2 vCPUs, 8 GB
    },
    "spot_discount": 0.91,  # Up to 91% discount for Spot VMs
    "cud_discount": 0.70,  # Up to 70% discount for 3-year CUD
    "persistent_disk": 0.17 / CLUSTER_HOURS,  # $0.17/GB/month converted to hourly
    "load_balancer": 0.025,  # $0.025/hour for HTTP load balancer
    "network_egress": 0.20,  # $0.20/GB
    "monitoring": 0.10,  # $0.10/GB for Cloud Monitoring
}

# Example workloads (pods) with resource requirements
WORKLOADS = [
    {"name": "frontend", "vcpu": 0.5, "memory": 1.0, "disk": 10, "egress": 5, "monitoring": 2},
    {"name": "backend", "vcpu": 1.0, "memory": 2.0, "disk": 20, "egress": 10, "monitoring": 5},
    {"name": "database", "vcpu": 1.5, "memory": 4.0, "disk": 50, "egress": 20, "monitoring": 10},
]

# Example nodes (each can be a different machine type)
NODES = [
    {"id": 0, "machine_type": "n1-standard-2"},
    {"id": 1, "machine_type": "e2-standard-2"},
    {"id": 2, "machine_type": "n1-standard-2"},
]

def optimize_gke_costs():
    try:
        # Create the solver (using CBC for linear programming)
        solver = pywraplp.Solver.CreateSolver("CBC")
        if not solver:
            raise ValueError("Solver not created. Ensure OR-Tools is installed correctly.")

        # Decision variables
        workload_to_node = {}
        for i, workload in enumerate(WORKLOADS):
            for j, node in enumerate(NODES):
                workload_to_node[i, j] = solver.BoolVar(f"workload_{workload['name']}_to_node_{j}")

        node_active = [solver.BoolVar(f"node_active_{j}") for j in range(len(NODES))]
        use_spot = [solver.BoolVar(f"use_spot_{j}") for j in range(len(NODES))]
        use_cud = [solver.BoolVar(f"use_cud_{j}") for j in range(len(NODES))]
        extra_cluster = solver.BoolVar("extra_cluster")

        # Auxiliary variables for compute cost
        cost_standard = [solver.NumVar(0, solver.infinity(), f"cost_standard_{j}") for j in range(len(NODES))]
        cost_spot = [solver.NumVar(0, solver.infinity(), f"cost_spot_{j}") for j in range(len(NODES))]
        cost_cud = [solver.NumVar(0, solver.infinity(), f"cost_cud_{j}") for j in range(len(NODES))]

        # Constraints
        # 1. Each workload must be assigned to exactly one node
        for i in range(len(WORKLOADS)):
            solver.Add(sum(workload_to_node[i, j] for j in range(len(NODES))) == 1)

        # 2. Resource constraints (CPU, memory) for each node
        for j, node in enumerate(NODES):
            machine_type = COST_DRIVERS["machine_types"][node["machine_type"]]
            solver.Add(
                sum(workload_to_node[i, j] * WORKLOADS[i]["vcpu"] for i in range(len(WORKLOADS)))
                <= machine_type["vcpu"] * node_active[j]
            )
            solver.Add(
                sum(workload_to_node[i, j] * WORKLOADS[i]["memory"] for i in range(len(WORKLOADS)))
                <= machine_type["memory"] * node_active[j]
            )

        # 3. Node usage: If a node has workloads, it must be active
        for j in range(len(NODES)):
            for i in range(len(WORKLOADS)):
                solver.Add(workload_to_node[i, j] <= node_active[j])

        # 4. At least one node must be active
        solver.Add(sum(node_active[j] for j in range(len(NODES))) >= 1)

        # 5. Cost selection and pricing model constraints
        for j in range(len(NODES)):
            solver.Add(use_spot[j] + use_cud[j] <= 1)
            print('###### 0.5.1')
            base_cost = COST_DRIVERS["machine_types"][NODES[j]["machine_type"]]["cost_per_hour"] * CLUSTER_HOURS
            print('###### 0.5.2')
            # Standard cost: Active when node is active and neither spot nor cud is used
            is_standard = solver.BoolVar(f"is_standard_{j}")
            solver.Add(is_standard >= 1 - use_spot[j] - use_cud[j])
            solver.Add(is_standard <= 1 - use_spot[j])
            solver.Add(is_standard <= 1 - use_cud[j])
            solver.Add(cost_standard[j] <= base_cost * node_active[j])
            solver.Add(cost_standard[j] <= base_cost * is_standard)
            solver.Add(cost_standard[j] >= base_cost * node_active[j] - BIG_M * (1 - is_standard))
            solver.Add(cost_standard[j] >= 0)
            print('###### 0.5.3')
            # Spot cost: Active when node is active and use_spot is 1
            solver.Add(cost_spot[j] <= base_cost * (1 - COST_DRIVERS["spot_discount"]) * node_active[j])
            solver.Add(cost_spot[j] <= base_cost * (1 - COST_DRIVERS["spot_discount"]) * use_spot[j])
            solver.Add(cost_spot[j] >= base_cost * (1 - COST_DRIVERS["spot_discount"]) * (node_active[j] + use_spot[j] - 1))
            solver.Add(cost_spot[j] >= 0)
            print('###### 0.5.4')
            # CUD cost: Active when node is active and use_cud is 1
            solver.Add(cost_cud[j] <= base_cost * (1 - COST_DRIVERS["cud_discount"]) * node_active[j])
            solver.Add(cost_cud[j] <= base_cost * (1 - COST_DRIVERS["cud_discount"]) * use_cud[j])
            solver.Add(cost_cud[j] >= base_cost * (1 - COST_DRIVERS["cud_discount"]) * (node_active[j] + use_cud[j] - 1))
            solver.Add(cost_cud[j] >= 0)
            print('###### 0.5.5')

        # Objective: Minimize total cost
        total_cost = solver.NumVar(0, solver.infinity(), "total_cost")

        # Compute costs
        compute_cost = sum(cost_standard[j] + cost_spot[j] + cost_cud[j] for j in range(len(NODES)))
        disk_cost = sum(
            sum(workload_to_node[i, j] * WORKLOADS[i]["disk"] for i in range(len(WORKLOADS)))
            * COST_DRIVERS["persistent_disk"] * CLUSTER_HOURS
            for j in range(len(NODES))
        )
        egress_cost = sum(
            sum(workload_to_node[i, j] * WORKLOADS[i]["egress"] for i in range(len(WORKLOADS)))
            * COST_DRIVERS["network_egress"]
            for j in range(len(NODES))
        )
        monitoring_cost = sum(
            sum(workload_to_node[i, j] * WORKLOADS[i]["monitoring"] for i in range(len(WORKLOADS)))
            * COST_DRIVERS["monitoring"]
            for j in range(len(NODES))
        )
        load_balancer_cost = COST_DRIVERS["load_balancer"] * CLUSTER_HOURS
        management_fee = extra_cluster * COST_DRIVERS["management_fee"] * CLUSTER_HOURS
        free_tier_savings = solver.NumVar(0, FREE_TIER_CREDIT, "free_tier_savings")
        solver.Add(free_tier_savings <= FREE_TIER_CREDIT)
        solver.Add(free_tier_savings <= management_fee)

        # Total cost constraint
        solver.Add(
            total_cost == compute_cost + disk_cost + egress_cost + monitoring_cost +
            load_balancer_cost + management_fee - free_tier_savings
        )

        # Set the objective to minimize total_cost
        solver.Minimize(total_cost)

        # Solve the problem
        status = solver.Solve()

        # Output results
        if status == pywraplp.Solver.OPTIMAL:
            print("Optimal Solution Found")
            print(f"Total Cost: ${total_cost.solution_value():.2f}")
            print("\nWorkload Assignments:")
            for i, workload in enumerate(WORKLOADS):
                for j, node in enumerate(NODES):
                    if workload_to_node[i, j].solution_value() > 0.5:
                        print(f"{workload['name']} assigned to Node {j} ({node['machine_type']})")
            print("\nNode Usage:")
            for j, node in enumerate(NODES):
                if node_active[j].solution_value() > 0.5:
                    spot = "Spot VM" if use_spot[j].solution_value() > 0.5 else ""
                    cud = "CUD" if use_cud[j].solution_value() > 0.5 else ""
                    pricing = spot or cud or "Standard"
                    print(f"Node {j} ({node['machine_type']}) is active ({pricing})")
            if extra_cluster.solution_value() > 0.5:
                print("Additional cluster management fee applied.")
            else:
                print("Free tier cluster management fee used.")
            print(f"Free Tier Savings: ${free_tier_savings.solution_value():.2f}")
        elif status == pywraplp.Solver.INFEASIBLE:
            raise ValueError("The problem is infeasible. Check resource constraints or workload requirements.")
        elif status == pywraplp.Solver.UNBOUNDED:
            raise ValueError("The problem is unbounded. Check cost calculations or constraints.")
        else:
            raise ValueError(f"Solver failed with status code: {status}")

    except Exception as e:
        print(f"Error occurred: {str(e)}")

def main():
    try:
        optimize_gke_costs()
    except Exception as e:
        print(f"Main error: {str(e)}")

if __name__ == "__main__":
    main()