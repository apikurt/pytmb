from typing import Literal, Optional, Union, overload

import requests

from pytmb.enums import TransitType
from pytmb.models.TransitModels.lines import LineInfo, LinesResponse
from pytmb.models.TransitModels.routes import (
    BusRouteInfo,
    BusRoutesConsolidatedResponse,
    BusRoutesResponse,
)


class TransitClient:
    def __init__(self, app_id: str = None, app_key: str = None):
        if app_id is None or app_key is None:
            raise ValueError("app_id and app_key must be provided")
        self.__app_id = app_id
        self.__app_key = app_key
        self.__base_url = "https://api.tmb.cat/v1/transit/"
        self.__default_params = {"app_id": self.__app_id, "app_key": self.__app_key}

    # Overloads for lines
    @overload
    def get_transit_lines(
        self,
        transit_type: TransitType | Literal["bus", "metro"],
        detail: Literal["summary"] = "summary",
        srs_name: Optional[str | int] = None,
    ) -> list[LineInfo]: ...

    @overload
    def get_transit_lines(
        self,
        transit_type: TransitType | Literal["bus", "metro"],
        detail: Literal["full"],
        srs_name: Optional[str | int] = None,
    ) -> LinesResponse: ...

    def get_transit_lines(
        self,
        transit_type: TransitType | Literal["bus", "metro"],
        detail: Literal["summary", "full"] = "summary",
        srs_name: Optional[str | int] = None,
    ) -> Union[list[LineInfo], LinesResponse]:
        """Retrieve available bus or metro lines.

        Args:
            transit_type: Transport mode (enum or "bus"/"metro").
            detail: "summary" (default) returns `list[LineInfo]`; "full" returns `LinesResponse`.
            srs_name: Optional spatial reference (e.g., 4326 or "EPSG:25831"). Passed as `srsName`.

        Returns:
            - When detail="summary": list of `LineInfo` objects with ergonomic fields.
            - When detail="full": a `LinesResponse` GeoJSON-like typed response.

        Docs:
            https://developer.tmb.cat/api-docs/v1/transit#tag/Linies
        """

        if isinstance(transit_type, TransitType):
            tt = transit_type.value
        elif isinstance(transit_type, str):
            tt = transit_type.lower()
        else:
            raise TypeError("transit_type must be TransitType or one of 'bus' | 'metro'")
        if tt not in ("bus", "metro"):
            raise ValueError("transit_type must be either 'bus' or 'metro'")

        endpoint = self.__base_url + f"linies/{tt}"
        params = self._params_with_srs(srs_name)

        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = LinesResponse.model_validate(response.json())
        if detail == "full":
            return data
        return [
            LineInfo(
                line_id=f.properties.line_id,
                line_code=f.properties.line_code,
                line_name=f.properties.line_name,
                operator_name=f.properties.operator_name,
                transport_type_name=f.properties.transport_type_name,
                line_origin=f.properties.line_origin,
                line_destination=f.properties.line_destination,
                color=f.properties.line_color,
            )
            for f in data.features
        ]

    # Overloads for detailed routes
    @overload
    def get_bus_routes(
        self, line_code: int, detail: Literal["summary"] = "summary", srs_name: Optional[str | int] = None
    ) -> list[BusRouteInfo]: ...

    @overload
    def get_bus_routes(
        self, line_code: int, detail: Literal["full"], srs_name: Optional[str | int] = None
    ) -> BusRoutesResponse: ...

    def get_bus_routes(
        self, line_code: int, detail: Literal["summary", "full"] = "summary", srs_name: Optional[str | int] = None
    ) -> Union[list[BusRouteInfo], BusRoutesResponse]:
        """Retrieve detailed bus routes for a specific bus line.

        Args:
            line_code: Bus line numeric code (e.g., 23).
            detail: "summary" (default) returns `list[BusRouteInfo]`; "full" returns `BusRoutesResponse`.
            srs_name: Optional spatial reference (e.g., 4326 or "EPSG:25831"). Passed as `srsName`.

        Returns:
            - When detail="summary": list of `BusRouteInfo` items.
            - When detail="full": a `BusRoutesResponse` GeoJSON-like typed response.

        Docs:
            https://developer.tmb.cat/api-docs/v1/transit#tag/Recorreguts/operation/recs
        """

        endpoint = self.__base_url + f"linies/bus/{line_code}/recs"
        params = self._params_with_srs(srs_name)

        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = BusRoutesResponse.model_validate(response.json())
        if detail == "full":
            return data
        return [
            BusRouteInfo(
                route_id=f.properties.route_id,
                line_code=f.properties.line_code,
                origin_name=f.properties.origin_name,
                destination_name=f.properties.destination_name,
                route_color=f.properties.route_color,
            )
            for f in data.features
        ]

    # Overloads for consolidated routes
    @overload
    def get_consolidated_bus_routes(
        self, line_code: int, detail: Literal["summary"] = "summary", srs_name: Optional[str | int] = None
    ) -> list[BusRouteInfo]: ...

    @overload
    def get_consolidated_bus_routes(
        self, line_code: int, detail: Literal["full"], srs_name: Optional[str | int] = None
    ) -> BusRoutesConsolidatedResponse: ...

    def get_consolidated_bus_routes(
        self, line_code: int, detail: Literal["summary", "full"] = "summary", srs_name: Optional[str | int] = None
    ) -> Union[list[BusRouteInfo], BusRoutesConsolidatedResponse]:
        """Retrieve consolidated bus routes (merged geometry) for a line.

        Args:
            line_code: Bus line numeric code (e.g., 23).
            detail: "summary" (default) returns `list[BusRouteInfo]`; "full" returns `BusRoutesConsolidatedResponse`.
            srs_name: Optional spatial reference (e.g., 4326 or "EPSG:25831"). Passed as `srsName`.

        Returns:
            - When detail="summary": list of `BusRouteInfo` items.
            - When detail="full": a `BusRoutesConsolidatedResponse` GeoJSON-like typed response.

        Docs:
            https://developer.tmb.cat/api-docs/v1/transit#tag/Recorreguts/operation/recs_cons
        """

        endpoint = self.__base_url + f"linies/bus/{line_code}/recs/cons"
        params = self._params_with_srs(srs_name)

        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = BusRoutesConsolidatedResponse.model_validate(response.json())
        if detail == "full":
            return data
        return [
            BusRouteInfo(
                route_id=f.properties.route_id,
                line_code=f.properties.line_code,
                origin_name=f.properties.origin_name,
                destination_name=f.properties.destination_name,
                route_color=f.properties.route_color,
            )
            for f in data.features
        ]

    def _params_with_srs(self, srs_name: Optional[str | int] = None) -> dict:
        params = dict(self.__default_params)
        if srs_name is not None:
            if isinstance(srs_name, int):
                params["srsName"] = f"EPSG:{srs_name}"
            else:
                sn = srs_name.strip()
                params["srsName"] = sn if sn.upper().startswith("EPSG:") else f"EPSG:{sn}"
        return params
