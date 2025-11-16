from time import time
from typing import Literal, Optional, Union, overload

import requests

from pytmb.models.iMetroModel import MetroEtaInfo, MetroEtaResponse


class IMetroClient:
    def __init__(self, app_id: str = None, app_key: str = None):
        if app_id is None or app_key is None:
            raise ValueError("app_id and app_key must be provided")
        self.__app_id = app_id
        self.__app_key = app_key
        self.__base_url = "https://api.tmb.cat/v1/itransit/metro/"
        self.__default_params = {"app_id": self.__app_id, "app_key": self.__app_key}

    @overload
    def get_eta(
        self, station_codes: list[int], line: Optional[str] = None, detail: Literal["summary"] = "summary"
    ) -> list[MetroEtaInfo]: ...

    @overload
    def get_eta(
        self, station_codes: list[int], line: Optional[str] = None, detail: Literal["full"] = ...
    ) -> MetroEtaResponse: ...

    def get_eta(
        self,
        station_codes: list[int],
        line: Optional[str] = None,
        detail: Literal["summary", "full"] = "summary",
    ) -> Union[list[MetroEtaInfo], MetroEtaResponse]:
        """Retrieve ETA for metro trains at one or more stations, optionally filtered by line.

        Args:
            station_codes: One or more station codes (integers as recorded by TMB).
            line: Optional line name filter (e.g. "L1"). Non-matching lines are omitted.
            detail: "summary" (default) returns `list[MetroEtaInfo]`; "full" returns `MetroEtaResponse`.

        Returns:
            - When detail="summary": list of `MetroEtaInfo` (flattened view across stations/routes).
            - When detail="full": `MetroEtaResponse` (raw typed payload).

        Docs:
            https://developer.tmb.cat/api-docs/v1/imetro#tag/Metodes/operation/previsioEstacio
        """
        if not station_codes or len(station_codes) == 0:
            raise ValueError("At least one station code must be provided")
        endpoint = self.__base_url + "estacions"
        response = requests.get(
            endpoint,
            params={**self.__default_params, "estacions": ",".join(str(code) for code in station_codes)},
            timeout=10,
        )
        response.raise_for_status()
        data = MetroEtaResponse.model_validate(response.json())

        # Show ETA for the specified line only if provided
        if line is not None:
            target = line.strip().lower()
            data.lines = [ml for ml in data.lines if ml.line_name.lower() == target]

        if detail == "full":
            return data

        return [
            MetroEtaInfo(
                line_code=metro_line.line_code,
                line_name=metro_line.line_name,
                line_color=metro_line.line_color,
                destination=route.destination,
                eta_minutes=((train.arrival_time - int(time() * 1000)) // 60000),
                station_code=station.station_code,
            )
            for metro_line in data.lines
            for station in metro_line.stations
            for route in station.line_routes
            for train in route.upcoming_trains
        ]
