# Response-first API

## Endpoint clients

`TMBClient` exposes `bus`, `metro`, `planner`, and `transit` groups sharing one
configured HTTP session. The corresponding standalone classes are `BusClient`,
`MetroClient`, `PlannerClient`, and `TransitClient`, exported from `pytmb`.

| Method | Response type | Independent summary helper |
| --- | --- | --- |
| `bus.fetch_eta(stop_code)` | `BusEtaResponse` | `summarize_bus(response)` → `BusArrivals` |
| `metro.fetch_eta(station_codes)` | `MetroEtaResponse` | `summarize_metro(response)` → `MetroArrivals` |
| `planner.fetch_plan(from_place, to_place, ...)` | `PlannerResponse` | `summarize_plan(response)` → `PlannerSummary` |
| `transit.fetch_lines(transit_type, ...)` | `LinesResponse` | `summarize_lines(response)` → `list[LineInfo]` |
| `transit.fetch_bus_routes(line_code, ...)` | `BusRoutesResponse` | `summarize_bus_routes(response)` → `list[BusRouteInfo]` |
| `transit.fetch_consolidated_bus_routes(line_code, ...)` | `BusRoutesConsolidatedResponse` | `summarize_bus_routes(response)` → `list[BusRouteInfo]` |

Every network method has one fixed response type. Planner options and transit
`srs_name` are keyword-only. Credentials are required constructor arguments.
Response/domain types are exported from `pytmb.models`; conversions are in
`pytmb.summaries`.

```python
from pytmb import TMBClient, TransitMode
from pytmb.models import BusEtaResponse, BusArrivals, ItinerarySummary
from pytmb.summaries import summarize_plan

with TMBClient(app_id, app_key) as client:
    response = client.planner.fetch_plan(
        (41.40, 2.18),
        (41.41, 2.16),
        mode=[TransitMode.BUS, TransitMode.WALK],
        show_intermediate_stops=True,
    )

view = summarize_plan(response)
fastest = min(view.itineraries, key=lambda itinerary: itinerary.duration, default=None)
```

## ETA snapshots

```python
from datetime import datetime, timezone
from pytmb.summaries import filter_bus, summarize_bus

with TMBClient(app_id, app_key) as client:
    response = client.bus.fetch_eta("1234")

snapshot = summarize_bus(response)
line_view = summarize_bus(response, line=" H10 ")
current_view = summarize_bus(response, at=datetime.now(timezone.utc))
typed_subset = filter_bus(response, "H10")

for arrival in current_view.arrivals:
    print(arrival.line_name, arrival.arrival_at, arrival.eta_minutes)
```

Helpers work after client closure and perform no HTTP calls. The same response
can produce multiple independent views. `BusArrivals` and `MetroArrivals` contain:

- `observed_at`: the upstream response timestamp, as an aware UTC `datetime`.
- `reference_time`: the instant used to calculate remaining arrival durations.
- `arrivals`: flattened predictions with UTC `arrival_at`, exact `eta` as a
  `timedelta`, and floored whole-minute `eta_minutes`.
- Direction and route identifiers, bus/operator identity, or metro track/service
  identity. Bus accessibility is nullable when it is unavailable.

Bus `line_code` retains an integer or string identifier: observed AMB services use
alphanumeric codes such as `N16`, while TMB uses numeric codes. Codes and display
names are distinct: TMB code `212`, for example, has display name `H12`. Vehicle
`bus_id` is nullable when the API omits it. Use the accompanying `transit_namespace`
and `operator_id` as identity context. Available ramp-status strings are preserved.

Metro route and service identifiers stay strings, including zero-prefixed route
codes such as `0011`. Arrival views retain each prediction's station, track, and
direction rather than merging the two directions at an interchange.

By default, `reference_time` equals `observed_at`. Conversion reads no wall clock,
so replaying a saved response is deterministic. Pass an explicit timezone-aware
`at` to calculate remaining durations at another instant; a naive `at` raises
`ValueError`. Explicit reference times are normalized to UTC without dropping
submillisecond precision.

Past arrivals are omitted by default. `include_past=True` retains their negative
durations; minute values are floored normally. An empty view still includes its
observation/reference metadata. Line matching ignores case and surrounding spaces.

## Planner views

`PlannerSummary` contains `plan_date`, `origin`, `destination`, and `itineraries`.
`plan_date` is the plan's original date timestamp converted to UTC. Each
`ItinerarySummary` includes:

- UTC `departure_at` and `arrival_at`.
- `duration` as a `timedelta`, plus `duration_seconds` and `duration_minutes` properties.
- Nullable `walk_time`, `transit_time`, and `waiting_time` timedeltas.
- Nullable `walk_distance` with fractional-meter precision, and nullable `transfers`.
- Independent copies of structured `legs`, including available route/trip IDs,
  places, geometry, steps, and intermediate stops.
- `overview` and `description` convenience strings produced during conversion.

Unknown metrics remain `None`; known zeros remain zero. Distances and fractional
minutes are preserved. Changing a view's places or legs does not modify the source
response. Walking-only journeys receive useful walking labels.

A successful empty plan produces an empty itinerary list with plan metadata.
`fetch_plan()` raises `APIError` for upstream application failures. Summarizing
a manually loaded error response or a response without a plan raises
`ResponseValidationError`.

## Typed-response and filtering policy

- Fetch methods return unfiltered typed responses, including all predictions and
  modeled collection metadata/geometry. Past predictions are retained.
- Root collections (`parades`, `linies`, and GeoJSON `features`) are required. An
  explicit empty list is a successful result; an absent collection is an invalid
  response and raises `ResponseValidationError` during a fetch.
- `filter_bus()` and `filter_metro()` return deep-copied typed subsets. Bus filters
  keep stops even when no routes match; metro filters select top-level lines.
- Response models ignore unknown upstream fields at modeled nesting levels and
  accept both wire aliases and Python field names. They apply their declared
  coercion/default rules. `model_dump(by_alias=True)` uses
  upstream field names for the modeled data; it is not a byte-for-byte payload copy.
- Transit summary lists select ergonomic properties. Geometry, CRS, counts, and
  available collection timestamps remain on the fetched response, including
  `total_features`, `number_matched`, `number_returned`, and `timestamp`.
- Domain-view models reject unexpected fields when constructing or reloading a
  view, so misspelled view fields are reported rather than silently discarded.

## Transit geometry and coordinate systems

Transit feature geometry is a discriminated union of `LineString` and
`MultiLineString`, exported from `pytmb.models`. The wire `type` selects its
coordinate structure. Python exposes that tag as `type_`:

```python
from pytmb.models import LineString

with TMBClient(app_id, app_key) as client:
    collection = client.transit.fetch_bus_routes(10, srs_name=25831)

for feature in collection.features:
    geometry = feature.geometry
    if isinstance(geometry, LineString):
        points = geometry.coordinates  # list[tuple[float, float]]
    else:
        lines = geometry.coordinates   # list[list[tuple[float, float]]]
```

Coordinates remain in the response CRS. For EPSG:4326, positions are
`(longitude, latitude)`; projected systems such as EPSG:25831 use projected `(x, y)`
values. The requested `srs_name` and response `crs` describe how to interpret them.
Geometry validation checks tags and nesting, without imposing geographic degree
bounds on projected data.

For standalone geometry validation, use `pydantic.TypeAdapter(Geometry)`.
Unmodeled tags or inconsistent nesting produce validation errors; during a fetch
these are wrapped in `ResponseValidationError` with field/type diagnostics.

Observed wire contracts and documentation deviations are recorded in
[`tests/fixtures/README.md`](tests/fixtures/README.md). Contract tests replay real
sanitized captures offline; additional wire-schema changes should be supported by
fresh observations because the published API documentation contains inaccuracies.
