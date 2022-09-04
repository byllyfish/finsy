import os

__version__ = "0.1.0"

# Must be set *before* importing `prometheus_client``.
os.environ["PROMETHEUS_DISABLE_CREATED_SERIES"] = str(True)
