# Upstream contract fixtures

The payloads in `tests/conftest.py` are synthetic regression inputs. The JSON files
here were captured from the real API on 2026-10-16 and sanitized before writing.
Each payload has a matching `.meta.json` file with its provenance. Contract tests
replay these files offline; test runs never refresh them or require credentials.

## Captured cases

| Fixture | Observation |
| --- | --- |
| `bus_eta` | Stop 108, AMB nighttime services: string codes such as `N16`; vehicle IDs omitted |
| `bus_eta_operating` | Stop 108 during service: mixed TMB/AMB codes, TMB vehicle IDs and ramp details, and AMB unknowns |
| `bus_eta_empty` | Stop 2775 returned HTTP 200 and an explicit empty `parades` list |
| `metro_eta` | L1 stations 115/123, both tracks; metadata present but no route predictions overnight |
| `metro_eta_running` | Seven active L1 predictions across both stations/tracks/directions, retaining service and zero-prefixed route codes |
| `metro_eta_empty` | Unknown station 999999 returned HTTP 200 and an explicit empty `linies` list |
| `bus_lines`, `metro_lines` | Representative bus 23 / metro L1 collections, selected by server-side filters |
| `bus_lines_empty` | A filter matching no bus line returned `features: []`, zero counts, and `crs: null` |
| `bus_routes`, `bus_routes_projected` | Bus 23 detailed routes in EPSG:4326 and EPSG:25831 |
| `bus_routes_consolidated` | Bus 23 consolidated route collection |
| `planner_transit` | Pl Espanya to Sagrada Familia, including walking, subway legs, and intermediate stops |
| `planner_walk` | Walking-only central Barcelona journey |
| `planner_empty` | Destination outside coverage returned a successful plan with no itineraries |
| `planner_invalid_mode` | Unsupported mode returned HTTP 500 with a JSON error; the SDK rejects that mode locally |
| `metro_stations_discovery` | Discovery-only public station data used to select valid prediction station codes; not a modeled SDK endpoint |
| `bus_stops_discovery` | Discovery-only public line 23 stop data; not a modeled SDK endpoint |

The capture-time `initial_model_validation` is historical diagnostics. It is not
rewritten after fixing a model: `bus_eta` intentionally records the original
integer-code / required-vehicle-ID failures.

## Observed model corrections

- AMB bus `codi_linia` values can be alphanumeric. Bus response/view models retain
  integer or string codes instead of forcing an integer conversion.
- `id_bus` is absent in the captured AMB predictions. It is nullable/optional in the
  response and nullable in the arrival view.
- The operating-hours snapshot confirms numeric TMB line codes and vehicle IDs,
  alongside alphanumeric AMB codes. For example, TMB code `212` has display name
  `H12`; its vehicle/ramp details are retained while AMB unknown values remain `None`.
- Successful empty bus, metro, and GeoJSON responses contain their root collection
  fields explicitly. Missing `parades`, `linies`, or `features` now fails validation
  instead of silently becoming an empty result.
- An out-of-coverage planner destination produced an empty itinerary list rather
  than an application error. Conversely, the invalid-mode request produced HTTP
  500 rather than the HTTP 400 one might expect from input validation.

## Refreshing or extending coverage

Add a new payload and matching `.meta.json` file when observing another real API
variant. Keep existing cases so changes to service availability or provider data
do not erase useful regressions. Record full decoded JSON without changing list
membership, field names, nulls, or missing fields. Replace credential echoes with
type-preserving placeholders and omit authentication parameters from provenance.

The offline contract tests discover new metadata files automatically. Use a model
name already registered in `tests/test_contracts.py`, or extend that registry when
adding an endpoint. Discovery-only captures use a null model name.

### Coverage status

The initial capture occurred around 03:00 Barcelona time. Additional captures at
11:38 cover active metro trains and TMB bus vehicle/accessibility details, closing
those operating-hours gaps. Earlier empty snapshots remain as off-hours cases.

The same live check also validated the complete unfiltered catalogues through the
public SDK: 114 bus lines and 11 metro lines, all with `MultiLineString` geometry.
Those full catalogues were checked in memory; focused recorded responses keep the
offline corpus manageable. These observations cover the recorded variants rather
than every possible future provider field or incident state.

## Provenance rules

For each captured JSON fixture, record its endpoint path, non-authentication query
parameters, capture date, status code, and coordinate reference system where
applicable. Remove credential values from URLs, echoed request parameters, and
messages; use public example locations instead of personal journey details.
Preserve field types, nulls, missing fields, and nesting.

When a captured response differs from the published documentation, record the
deviation with the fixture and add a regression test for the observed contract.
Required-field or endpoint changes should be supported by these observations.
