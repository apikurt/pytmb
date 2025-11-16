# PyTMB

Unofficial Python client for the Barcelona public transport (TMB) API.

> This library is not affiliated with TMB. Use responsibly and respect the API Terms of Service.

## Features

- Bus ETA lookup (`IBusClient.get_eta`)
- Metro ETA lookup (`IMetroClient.get_eta`)
- Planner routing with summary or full detail (`PlannerClient.calculate_routes`)
- Summary-by-default overloads (`detail="full"` for raw typed responses)
- Pydantic models for structured responses; simple sync API using `requests`

## Requirements

- Python >= 3.10
- `app_id` and `app_key` from TMB's developer portal.
    - Register at: https://developer.tmb.cat/

## Installation

PyPI:

```bash
pip install pytmb
```

From source (clone this repository):

```bash
pip install .
```

## Quick Start

```python
from pytmb import IBusClient, IMetroClient, PlannerClient

BUS_STOP_CODE = "1234"        # Replace with a real stop code
METRO_STATIONS = [123, 456]    # Replace with real station codes

app_id = "YOUR_APP_ID"
app_key = "YOUR_APP_KEY"

# Bus ETA
bus_client = IBusClient(app_id=app_id, app_key=app_key)
bus_etas = bus_client.get_eta(BUS_STOP_CODE, line="H10")  # default: summarized objects (list[BusEtaInfo])
for eta in bus_etas:
	print(f"Bus {eta.line_name} to {eta.destination} arriving in {eta.eta_minutes} min (ramp={eta.ramp_status})")

# Or get the full raw response (typed)
bus_raw = bus_client.get_eta(BUS_STOP_CODE, detail="full")  # -> BusEtaResponse
print(bus_raw.timestamp, len(bus_raw.stops))

# Metro ETA
metro_client = IMetroClient(app_id=app_id, app_key=app_key)
metro_etas = metro_client.get_eta(METRO_STATIONS, line="L1")  # summarized by default (list[MetroEtaInfo])
for eta in metro_etas:
	print(f"Metro {eta.line_name} to {eta.destination} arriving in {eta.eta_minutes} min at station {eta.station_code}")

# Or full raw response
metro_raw = metro_client.get_eta(METRO_STATIONS, detail="full")  # -> MetroEtaResponse
print(metro_raw.timestamp, len(metro_raw.lines))

# Planner (summary by default)
planner = PlannerClient(app_id=app_id, app_key=app_key)
itins = planner.calculate_routes((41.40, 2.18), (41.41, 2.16))  # list[PlannerItineraryInfo]
for i in itins[:3]:  # show first few
	print(i.overview, i.duration_in_minutes, "min")

# Full planner response
full_plan = planner.calculate_routes((41.40, 2.18), (41.41, 2.16), detail="full")  # -> PlannerResponse
print(len(full_plan.plan.itineraries) if full_plan.plan else 0)
```

## Roadmap / Ideas

- Transit lines & routes re-enabled once completed
- Additional endpoints (stops, alerts)

## License

See `LICENSE` file.

## Disclaimer

All trademarks and data belong to TMB. This is a community project.
