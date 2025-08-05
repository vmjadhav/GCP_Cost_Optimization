from pathlib import Path

# Get the project root directory (where config.py is located)
PROJECT_ROOT = Path(__file__).resolve().parent
# Path to the shared file (e.g., service account JSON)
SERVICE_ACCOUNT_KEY = PROJECT_ROOT / "abc.json"
#print('SERVICE_ACCOUNT_KEY ===>> ', SERVICE_ACCOUNT_KEY)
PROJECT_ID = 'cost-optimization-467817'
REGION = 'us'
