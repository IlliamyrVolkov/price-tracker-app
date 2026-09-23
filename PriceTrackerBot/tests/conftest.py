import os
import sys
from pathlib import Path

# The app imports its packages as top level modules (PYTHONPATH=/app/app in Docker).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

# Settings are read at import time; tests must never pick up the real token from .env.
os.environ.update({
    "TG__TOKEN": "123456:TEST",
    "KAFKA__BOOTSTRAP_SERVERS": "kafka:9092",
    "KAFKA__TOPIC": "price-updates",
    "RPC__HOST": "backend",
    "RPC__PORT": "50051",
})
