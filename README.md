<h1 align="center">PyTMB</h1>

<p align="center">
  <strong>Barcelona transit data, with a typed Python API.</strong><br>
  Bus and metro arrivals · journey planning · lines and routes
</p>

<p align="center">
  <a href="https://pypi.org/project/pytmb/"><img src="https://img.shields.io/pypi/v/pytmb?style=flat-square&color=007ec6" alt="PyPI version"></a>
  <a href="https://github.com/apikurt/pytmb/actions/workflows/checks.yml"><img src="https://img.shields.io/github/actions/workflow/status/apikurt/pytmb/checks.yml?branch=main&style=flat-square&label=CI" alt="CI status"></a>
  <a href="https://pypi.org/project/pytmb/"><img src="https://img.shields.io/pypi/pyversions/pytmb?style=flat-square" alt="Supported Python versions"></a>
  <a href="https://github.com/apikurt/pytmb/blob/main/src/pytmb/py.typed"><img src="https://img.shields.io/badge/typing-typed-22863a?style=flat-square" alt="Typed Python package"></a>
  <a href="https://github.com/apikurt/pytmb/blob/main/LICENSE"><img src="https://img.shields.io/github/license/apikurt/pytmb?style=flat-square" alt="MIT license"></a>
</p>

<p align="center">
  <a href="https://github.com/apikurt/pytmb/blob/main/API.md">API guide</a> ·
  <a href="https://pypi.org/project/pytmb/">PyPI</a> ·
  <a href="https://github.com/apikurt/pytmb/releases">Releases</a> ·
  <a href="https://github.com/apikurt/pytmb/issues">Issues</a>
</p>

PyTMB is an unofficial, synchronous client for the [TMB API](https://developer.tmb.cat/). Fetch validated responses, then turn them into useful arrival and journey views—without making another request.

- **Typed results:** Pydantic models, editor-friendly return types, and a `py.typed` package.
- **One client:** bus, metro, planner, and transit groups share a persistent HTTP session.
- **Useful views:** arrival times, directions, tracks, accessibility details, and structured journey legs.
- **Predictable HTTP:** configurable timeouts, bounded retries, credential-safe errors, and explicit cleanup.
- **Real contract coverage:** offline regression tests replay sanitized responses captured from TMB.

## Installation

Requires **Python 3.10+** and an `app_id` / `app_key` from the [TMB developer portal](https://developer.tmb.cat/).

```bash
pip install pytmb
```

Set your credentials in the environment as `APP_ID` and `APP_KEY`, or pass them directly to the client constructor.

**0.2.0 introduces a redesigned public API.** Earlier `get_eta` and `calculate_routes` interfaces have been replaced by the response-first API below.

## Quick start

```python
import os
from datetime import datetime, timezone

from pytmb import TMBClient
from pytmb.summaries import summarize_bus

with TMBClient(os.environ["APP_ID"], os.environ["APP_KEY"]) as client:
    response = client.bus.fetch_eta("108")  # Pl Espanya - FGC

# The response is still usable after the client closes.
view = summarize_bus(response, line="H12", at=datetime.now(timezone.utc))
for arrival in view.arrivals:
    print(f"{arrival.line_name} → {arrival.destination}: {arrival.eta_minutes} min")
```

`fetch_*` methods always return a complete typed response. Summary helpers are independent transformations: they perform no HTTP requests and do not mutate the input. Keep a response to create several views or recalculate remaining arrival times later.

### Metro and journey planning

```python
import os

from pytmb import TMBClient, TransitMode
from pytmb.summaries import summarize_metro, summarize_plan

with TMBClient(os.environ["APP_ID"], os.environ["APP_KEY"]) as client:
    metro = client.metro.fetch_eta([123, 115])  # Rocafort and Can Serra
    plan = client.planner.fetch_plan(
        (41.3755204, 2.1498870),  # Pl Espanya
        (41.403629, 2.174356),    # Sagrada Familia
        mode=[TransitMode.TRANSIT, TransitMode.WALK],
        show_intermediate_stops=True,
    )

for train in summarize_metro(metro, line="L1").arrivals:
    print(train.destination, train.station_code, train.track, train.eta_minutes)

for journey in summarize_plan(plan).itineraries:
    print(journey.overview, journey.duration_minutes, journey.departure_at)
    for leg in journey.legs:
        print(leg.mode, leg.from_.name, leg.to.name)
```

### Lines and route geometry

```python
import os

from pytmb import TMBClient
from pytmb.summaries import summarize_lines

with TMBClient(os.environ["APP_ID"], os.environ["APP_KEY"]) as client:
    lines = client.transit.fetch_lines("bus")
    routes = client.transit.fetch_bus_routes(23, srs_name=25831)

print([line.line_name for line in summarize_lines(lines)])
for feature in routes.features:
    print(feature.properties.destination_name, feature.geometry.type_)
```

## API at a glance

| Group | Method | Response |
| --- | --- | --- |
| Bus | `client.bus.fetch_eta(stop_code)` | `BusEtaResponse` |
| Metro | `client.metro.fetch_eta(station_codes)` | `MetroEtaResponse` |
| Planner | `client.planner.fetch_plan(from_place, to_place, ...)` | `PlannerResponse` |
| Transit | `client.transit.fetch_lines(transit_type)` | `LinesResponse` |
| Transit | `client.transit.fetch_bus_routes(line_code)` | `BusRoutesResponse` |
| Transit | `client.transit.fetch_consolidated_bus_routes(line_code)` | `BusRoutesConsolidatedResponse` |

Models are exported from `pytmb.models`. Standalone `BusClient`, `MetroClient`, `PlannerClient`, and `TransitClient` support the same HTTP options as `TMBClient`.

See the **[API guide](https://github.com/apikurt/pytmb/blob/main/API.md)** for summary types, filtering, field semantics, and coordinate systems.

### Data semantics

- **Time:** summary datetimes are UTC-aware; durations use `timedelta`. Planner defaults use Barcelona time.
- **Snapshots:** ETA helpers use the response timestamp by default. Pass an aware `at` for another reference time.
- **Availability:** past arrivals are omitted from summaries by default; fetched responses retain them.
- **Unknown values:** unavailable vehicle IDs, accessibility details, and optional journey metrics remain `None`.
- **Identifiers:** bus codes can be numeric or alphanumeric; metro route codes retain leading zeros.
- **Geometry:** `LineString` and `MultiLineString` preserve coordinates in the requested response CRS.
- **Validation:** missing root collections fail validation; explicit empty collections are successful results.

## HTTP configuration

```python
import os

from pytmb import TMBClient

with TMBClient(
    os.environ["APP_ID"],
    os.environ["APP_KEY"],
    timeout=(3, 15),  # connect and read timeouts, in seconds
    max_retries=2,
    backoff_factor=0.5,
    max_retry_delay=30,
) as client:
    response = client.bus.fetch_eta("108")
```

| Option | Default | Purpose |
| --- | --- | --- |
| `timeout` | `10` | Per-attempt timeout, or a `(connect, read)` pair |
| `max_retries` | `2` | Additional GET attempts; `0` disables retries |
| `backoff_factor` | `0.5` | Initial exponential retry delay in seconds |
| `max_retry_delay` | `30` | Maximum automatic delay between attempts |
| `session` | Created internally | Optional caller-owned `requests.Session` |
| `base_url` | `https://api.tmb.cat/v1/` | Common API root |

Retries cover HTTP 429/500/502/503/504, timeouts, and selected connection failures. `Retry-After` takes precedence over backoff. If the required delay exceeds the limit, the client raises `HTTPError` with `retry_after` instead of retrying early.

Use `with` or call `close()` when finished. Injected sessions stay caller-owned. The facade's timeout applies to every group; a standalone `PlannerClient` defaults to 15 seconds.

## Error handling

```python
import os

from pytmb import HTTPError, TMBClient, TMBError

try:
    with TMBClient(os.environ["APP_ID"], os.environ["APP_KEY"]) as client:
        response = client.bus.fetch_eta("108")
except HTTPError as exc:
    print(exc.status_code, exc.request_id, exc.retry_after)
except TMBError as exc:
    print(type(exc).__name__, str(exc))
```

Transport, HTTP, API, and response-validation failures derive from `TMBError`. Errors expose useful context while redacting credentials; response validation diagnostics omit raw inputs. Invalid request arguments raise `ValueError`.

## Development

From a source checkout:

```bash
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check src tests
uv run --locked mypy
uv build --no-sources
```

Tests run offline with dummy credentials and include both synthetic edge cases and sanitized live captures. The [fixture guide](https://github.com/apikurt/pytmb/blob/main/tests/fixtures/README.md) records provenance and observed API behavior.

CI covers Python **3.10–3.14 on Linux**, Python **3.10/3.14 on Windows**, linting, typing, and isolated installation checks for the wheel and source distribution. Version tags run the same checks before publishing the tested artifacts to PyPI.

## License

[MIT](https://github.com/apikurt/pytmb/blob/main/LICENSE). PyTMB is not affiliated with TMB. Transport data and trademarks belong to their respective owners.
