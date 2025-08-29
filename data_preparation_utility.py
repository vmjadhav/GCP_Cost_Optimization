import pandas as pd
import numpy as np
import pprint
from datetime import datetime, timedelta
from data_utility import dummy_bigquery_mixed_data

# Assuming you already have dummy_bigquery_mixed_data

df = dummy_bigquery_mixed_data.copy()

# --- STEP 1: Create unique creation_time values ---
# Start from earliest creation_time in the data
start_time = datetime(2025, 8, 14, 18, 0, 0)
time_increment = timedelta(minutes=5)  # increment each row by 5 minutes

df = df.sort_values(by='creation_time').reset_index(drop=True)
df['creation_time'] = [ (start_time + i*time_increment).strftime("%Y-%m-%dT%H:%M:%SZ") 
                        for i in range(len(df)) ]

# --- STEP 2: Redistribute total_bytes_processed ---
n = len(df)

# Define percentages
mean_group_pct = 0.6
std_group_pct = 0.4

mean_group_size = int(n * mean_group_pct)
std_group_size = n - mean_group_size

# Base mean value — pick some realistic BigQuery processed bytes (e.g., 1 TiB)
mean_bytes = 5001099511627776  # 1 TiB in bytes

# 60% group — generate values close to mean (±5%)
mean_group_values = np.random.normal(loc=mean_bytes, scale=mean_bytes*0.05, size=mean_group_size).astype(int)

# 40% group — generate more varied values (±50%)
std_group_values = np.random.normal(loc=mean_bytes, scale=mean_bytes*0.5, size=std_group_size).astype(int)

# Ensure no negative values
mean_group_values = np.clip(mean_group_values, 0, None)
std_group_values = np.clip(std_group_values, 0, None)

# Combine and shuffle
new_bytes_processed = np.concatenate([mean_group_values, std_group_values])
np.random.shuffle(new_bytes_processed)

df['total_bytes_processed'] = new_bytes_processed

# --- Check distribution ---
mean_60 = df['total_bytes_processed'][:mean_group_size].mean()
std_40 = df['total_bytes_processed'][mean_group_size:].std()

print(f"Mean of ~60% group: {mean_60/1024**4:.2f} TiB")
print(f"Std Dev of ~40% group: {std_40/1024**4:.2f} TiB")

# Convert DataFrame to list of dicts
data_list = df.to_dict(orient="records")

# Pretty print with indentation so it matches your original style
pp = pprint.PrettyPrinter(indent=2, width=120, sort_dicts=False)
pp.pprint(data_list)
