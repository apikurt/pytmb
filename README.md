# PyTMB

Unofficial Python client for the Barcelona public transport (TMB) API.

> This library is not affiliated with TMB. Use responsibly and respect the API Terms of Service.

## Features
- Bus ETA lookup (`IBusClient.get_eta`)
- Metro ETA lookup (`IMetroClient.get_eta`)
- Optional filtering by line
- Pydantic models for structured responses
- Simple, synchronous API using `requests`

## Requirements
- Python >= 3.10

## Installation
PyPI:
```bash
pip install pytmb
```

From source (clone this repository):
```bash
pip install .
```

## API Credentials
You need an `app_id` and `app_key` from TMB's developer portal.
Register at: https://developer.tmb.cat/

## Quick Start
```python
from pytmb.iBus import IBusClient
from pytmb.iMetro import IMetroClient

BUS_STOP_CODE = "1234"          # Replace with a real stop code
METRO_STATIONS = ["123", "456"] # Replace with real station codes

app_id = "YOUR_APP_ID"
app_key = "YOUR_APP_KEY"

# Bus ETA
bus_client = IBusClient(app_id=app_id, app_key=app_key)
bus_etas = bus_client.get_eta(BUS_STOP_CODE, line="H10")  # Optionally filter by line
for eta in bus_etas:
	print(f"Bus {eta.line_name} to {eta.destination} arriving in {eta.eta_minutes} min (ramp={eta.ramp_status})")

# Metro ETA
metro_client = IMetroClient(app_id=app_id, app_key=app_key)
metro_etas = metro_client.get_eta(METRO_STATIONS, line="L1")
for eta in metro_etas:
	print(f"Metro {eta.line_name} to {eta.destination} arriving in {eta.eta_minutes} min at station {eta.station_code}")
```

## Roadmap / Ideas
- Coverage for more TMB endpoints

## License
See `LICENSE` file.

## Disclaimer
All trademarks and data belong to TMB. This is a community project.