from time import time
from typing import Literal, Optional, Union, overload

import requests

from pytmb.models.iBusModel import BusEtaInfo, BusEtaResponse


class IBusClient:
    def __init__(self, app_id: str = None, app_key: str = None):
        if app_id is None or app_key is None:
            raise ValueError("app_id and app_key must be provided")
        self.__app_id = app_id
        self.__app_key = app_key
        self.__base_url = "https://api.tmb.cat/v1/itransit/bus/"
        self.__default_params = {"app_id": self.__app_id, "app_key": self.__app_key}

    @overload
    def get_eta(
        self, stop_code: str, line: Optional[str] = None, detail: Literal["summary"] = "summary"
    ) -> list[BusEtaInfo]: ...

    @overload
    def get_eta(self, stop_code: str, line: Optional[str] = None, detail: Literal["full"] = ...) -> BusEtaResponse: ...

    def get_eta(
        self, stop_code: str, line: Optional[str] = None, detail: Literal["summary", "full"] = "summary"
    ) -> Union[list[BusEtaInfo], BusEtaResponse]:
        """Retrieve ETA for buses at a stop, with optional line filter.

        Args:
            stop_code: Bus stop code (string displayed by TMB).
            line: Optional line name to filter results (case-insensitive, e.g. "H10").
            detail: "summary" (default) returns `list[BusEtaInfo]`; "full" returns `BusEtaResponse`.

        Returns:
            - When detail="summary": list of `BusEtaInfo` (flattened, ergonomic view).
            - When detail="full": `BusEtaResponse` (raw typed payload).

        Docs:
            https://developer.tmb.cat/api-docs/v1/ibus#tag/Metodes/operation/previsioParada
        """
        endpoint = self.__base_url + f"parades/{stop_code}"
        response = requests.get(endpoint, params=self.__default_params, timeout=10)
        response.raise_for_status()
        data = BusEtaResponse.model_validate(response.json())

        # Show ETA for the specified line only
        if line is not None:
            for stop in data.stops:
                stop.line_routes = [route for route in stop.line_routes if route.line_name.lower() == line.lower()]

        if detail == "full":
            return data

        return [
            BusEtaInfo(
                line_code=route.line_code,
                line_name=route.line_name,
                destination=route.destination,
                eta_minutes=(bus.arrival_time - time() * 1000) // 60000,
                stop_code=stop.stop_code,
                ramp_status=(bus.info.accessibility.ramp_status if bus.info and bus.info.accessibility else "Unknown"),
            )
            for stop in data.stops
            for route in stop.line_routes
            for bus in route.upcoming_buses
        ]

    # (no internal helpers; logic kept inline for simplicity)
