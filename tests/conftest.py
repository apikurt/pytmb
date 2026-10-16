"""Synthetic regression payloads, not captured upstream schema fixtures."""

from unittest.mock import Mock

import pytest
import requests
from requests.adapters import HTTPAdapter


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    monkeypatch.setattr(
        HTTPAdapter, "send", Mock(side_effect=AssertionError("Unexpected network request"))
    )


@pytest.fixture
def http_get(monkeypatch):
    get = Mock(side_effect=AssertionError("Unexpected HTTP request in an offline test"))
    monkeypatch.setattr(requests.Session, "get", get)
    return get


@pytest.fixture
def make_response():
    def create(payload, *, status=200, headers=None):
        response = Mock(spec=requests.Response)
        response.status_code = status
        response.headers = headers or {}
        response.json.return_value = payload
        return response

    return create


@pytest.fixture
def respond(http_get, make_response):
    def set_response(payload):
        response = make_response(payload)
        http_get.side_effect = None
        http_get.return_value = response
        return response

    return set_response


@pytest.fixture
def planner_payload():
    origin = {"name": "Origin", "lat": 41.4, "lon": 2.18}
    destination = {"name": "Destination", "lat": 41.41, "lon": 2.16}
    return {
        "plan": {
            "date": 1000000,
            "from": origin,
            "to": destination,
            "itineraries": [
                {
                    "duration": 600,
                    "startTime": 1000000,
                    "endTime": 1600000,
                    "transitTime": 600,
                    "waitingTime": 0,
                    "walkDistance": 0,
                    "transfers": 0,
                    "legs": [
                        {
                            "mode": "BUS",
                            "route": "H10",
                            "startTime": 1000000,
                            "endTime": 1600000,
                            "duration": 600,
                            "distance": 500.0,
                            "from": origin,
                            "to": destination,
                        }
                    ],
                }
            ],
        }
    }


@pytest.fixture
def bus_payload():
    return {
        "timestamp": 1000000,
        "parades": [
            {
                "codi_parada": "1234",
                "nom_parada": "Test stop",
                "linies_trajectes": [
                    {
                        "id_operador": 1,
                        "transit_namespace": "bus",
                        "codi_linia": 10,
                        "nom_linia": "H10",
                        "id_sentit": 1,
                        "codi_trajecte": "10",
                        "desti_trajecte": "Destination",
                        "propers_busos": [
                            {"temps_arribada": arrival, "id_bus": index}
                            for index, arrival in enumerate([999000, 1000000, 1059999, 1060000], start=1)
                        ],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def metro_payload():
    return {
        "timestamp": 1000000,
        "linies": [
            {
                "codi_linia": 1,
                "nom_linia": "L1",
                "nom_familia": "Metro",
                "codi_familia": 1,
                "color_linia": "FF0000",
                "estacions": [
                    {
                        "codi_via": 1,
                        "id_sentit": 1,
                        "codi_estacio": 123,
                        "linies_trajectes": [
                            {
                                "codi_linia": 1,
                                "nom_linia": "L1",
                                "color_linia": "FF0000",
                                "codi_trajecte": "1",
                                "desti_trajecte": "Destination",
                                "propers_trens": [
                                    {"temps_arribada": arrival, "codi_servei": str(index)}
                                    for index, arrival in enumerate([999000, 1000000, 1059999, 1060000], start=1)
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def lines_payload():
    return {
        "type": "FeatureCollection",
        "totalFeatures": 1,
        "numberReturned": 1,
        "timeStamp": "2026-10-16T10:00:00Z",
        "features": [
            {
                "type": "Feature",
                "id": "line-10",
                "geometry_name": "GEOMETRY",
                "geometry": {"type": "LineString", "coordinates": [[2.18, 41.4], [2.16, 41.41]]},
                "properties": {
                    "CODI_FAMILIA": 1,
                    "CODI_LINIA": 10,
                    "CODI_TIPUS_CALENDARI": "1",
                    "COLOR_AUX_LINIA": "FFFFFF",
                    "COLOR_LINIA": "FF0000",
                    "COLOR_TEXT_LINIA": "000000",
                    "DESC_LINIA": "Origin / Destination",
                    "NOM_TIPUS_CALENDARI": "Daily",
                    "DESTI_LINIA": "Destination",
                    "ID_LINIA": 100,
                    "ID_OPERADOR": 1,
                    "NOM_FAMILIA": "Bus",
                    "NOM_LINIA": "H10",
                    "NOM_OPERADOR": "TMB",
                    "NOM_TIPUS_TRANSPORT": "BUS",
                    "ORDRE_FAMILIA": 1,
                    "ORDRE_LINIA": 10,
                    "ORIGEN_LINIA": "Origin",
                },
            }
        ],
    }


@pytest.fixture
def routes_payload():
    return {
        "type": "FeatureCollection",
        "totalFeatures": 1,
        "features": [
            {
                "type": "Feature",
                "id": "route-1000",
                "geometry_name": "GEOMETRY",
                "geometry": {"type": "LineString", "coordinates": [[2.18, 41.4], [2.16, 41.41]]},
                "properties": {
                    "ID_RECORREGUT": 1000,
                    "ID_LINIA": 100,
                    "CODI_LINIA": 10,
                    "NOM_LINIA": "H10",
                    "DESC_LINIA": "Origin / Destination",
                    "ORIGEN_SENTIT": "Origin",
                    "DESTI_SENTIT": "Destination",
                    "ORDRE_LINIA": 10,
                    "ID_OPERADOR": 1,
                    "NOM_OPERADOR": "TMB",
                    "CODI_FAMILIA": 1,
                    "NOM_FAMILIA": "Bus",
                    "ORDRE_FAMILIA": 1,
                    "ID_TIPUS_DIA": 1,
                    "ID_TIPUS_DIA_EMULAT": 0,
                    "NOM_TIPUS_DIA": "Daily",
                    "ID_SENTIT": 1,
                    "SENTIT": "A",
                    "DESC_SENTIT": "Outbound",
                    "ID_TIPUS_RECORREGUT": 1,
                    "DESC_TIPUS_RECORREGUT": "Commercial",
                    "ID_TIPUS_SERVEI": 1,
                    "DESC_SERVEI": "Regular",
                    "ID_TIPUS_SUB_SERVEI": 1,
                    "DESC_SUB_SERVEI": "Regular",
                    "COLOR_REC": "FF0000",
                    "LONGITUD": 500.25,
                    "LONGITUD_CARRIL_BUS": 100.5,
                },
            }
        ],
    }
