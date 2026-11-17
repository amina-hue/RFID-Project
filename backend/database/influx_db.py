"""Connexion à InfluxDB, partagée par les services."""
import os

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "token-de-dev-123")
INFLUX_ORG = os.getenv("INFLUX_ORG", "projet")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acces")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()