from ortools.math_opt.python import mathopt
import pandas as pd
from google.cloud import storage, bigquery

# Initialize GCP clients
storage_client = storage.Client()
bq_client = bigquery.Client()

# Load data from GCS
bucket = storage_client.get_bucket("my-bucket")
blob = bucket.get_blob("query_data.csv")
query_data = pd.read_csv(blob.download_as_string())
blob = bucket.get_blob("cost_data.csv")
cost_data = pd.read_csv(blob.download_as_string())

# Create MathOpt model
model = mathopt.Model(name="bigquery_cost_optimization")

# Variables: slots per project
slots = {}
for idx, row in query_data.iterrows():
    project_id = row["project_id"]
    slots[project_id] = model.add_variable(lb=row["min_slots"], ub=1000, is_integer=False, name=f"slots_{project_id}")

# Objective: Minimize total cost
cost_expr = 0
for idx, row in query_data.iterrows():
    project_id = row["project_id"]
    cost_per_byte = cost_data[cost_data["project_id"] == project_id]["cost_per_byte"].iloc[0]
    slot_cost = cost_data[cost_data["project_id"] == project_id]["slot_cost"].iloc[0]
    cost_expr += (row["avg_bytes"] * cost_per_byte + slots[project_id] * slot_cost) * row["priority"]

model.minimize(cost_expr)

# Constraint: Total slots <= 2000
model.add_linear_constraint(sum(slots.values()) <= 2000, name="total_slots")

# Solve using GCP OR API (GLOP solver)
params = mathopt.SolveParameters()
result = mathopt.solve(model, mathopt.SolverType.GLOP, params=params, api_key="your_or_api_key")

# Output results
if result.termination_reason == mathopt.TerminationReason.OPTIMAL:
    print(f"Optimal cost: {result.objective_value()}")
    for project_id, var in slots.items():
        print(f"Project {project_id}: {result.variable_values()[var]} slots")
else:
    print("No optimal solution found.")

# Store results in BigQuery
result_df = pd.DataFrame({
    "project_id": slots.keys(),
    "allocated_slots": [result.variable_values()[var] for var in slots.values()]
})
result_df.to_gbq("project.dataset.optimization_results", project_id="your_project")