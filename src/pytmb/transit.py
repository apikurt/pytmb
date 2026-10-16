from typing import Literal

from pytmb._endpoint import EndpointClient
from pytmb.enums import TransitType
from pytmb.models.transit.lines import LinesResponse
from pytmb.models.transit.routes import BusRoutesConsolidatedResponse, BusRoutesResponse


class TransitClient(EndpointClient):
    """Transit reference data returned as typed geospatial collections."""

    def fetch_lines(
        self, transit_type: TransitType | Literal["bus", "metro"], *, srs_name: str | int | None = None
    ) -> LinesResponse:
        """Fetch line data, including geometry and collection metadata."""
        if isinstance(transit_type, TransitType):
            mode = transit_type.value
        elif isinstance(transit_type, str):
            mode = transit_type.lower()
        else:
            raise TypeError("transit_type must be TransitType or one of 'bus' | 'metro'")
        if mode not in ("bus", "metro"):
            raise ValueError("transit_type must be either 'bus' or 'metro'")
        return self._get(f"transit/linies/{mode}", LinesResponse, params=self._params_with_srs(srs_name))

    def fetch_bus_routes(self, line_code: int, *, srs_name: str | int | None = None) -> BusRoutesResponse:
        """Fetch the detailed bus-route collection."""
        return self._get(
            f"transit/linies/bus/{line_code}/recs", BusRoutesResponse, params=self._params_with_srs(srs_name)
        )

    def fetch_consolidated_bus_routes(
        self, line_code: int, *, srs_name: str | int | None = None
    ) -> BusRoutesConsolidatedResponse:
        """Fetch the consolidated bus-route collection."""
        return self._get(
            f"transit/linies/bus/{line_code}/recs/cons",
            BusRoutesConsolidatedResponse,
            params=self._params_with_srs(srs_name),
        )

    @staticmethod
    def _params_with_srs(srs_name: str | int | None) -> dict[str, str]:
        if srs_name is None:
            return {}
        if isinstance(srs_name, int):
            return {"srsName": f"EPSG:{srs_name}"}
        value = srs_name.strip()
        return {"srsName": value if value.upper().startswith("EPSG:") else f"EPSG:{value}"}
