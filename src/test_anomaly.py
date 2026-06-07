import logging
from src.anomaly.detector import detect_anomalies
from src.etl.load import insert_anomalies

logging.basicConfig(level=logging.INFO)

print("Starting anomaly detection...")
records = detect_anomalies(1)  # AAPL is 1
print("DETECTED", len(records), "records")

print("Inserting records...")
insert_anomalies(records)
print("DONE")
