from time import time
from typing import Optional

import requests

from pytmb.models.iBusModel import BusEta, EtaResponseBus


class IBusClient:
    def __init__(self, app_id: str = None, app_key: str = None):
        if app_id is None or app_key is None:
            raise ValueError("app_id and app_key must be provided")
        self.__app_id = app_id
        self.__app_key = app_key
        self.__base_url = "https://api.tmb.cat/v1/itransit/bus/"
        self.__default_params = {"app_id": self.__app_id, "app_key": self.__app_key}

    def get_eta(self, stop_code: str, line: Optional[str] = None) -> list[BusEta]:
        """Get the estimated time of arrival (ETA) for buses at a specific stop.

        Args:
            stop_code (str): The code of the bus stop.
            line (Optional[str]): The bus line to filter by. Defaults to None and shows all lines.
        Returns:
            list[BusEta]: List of BusEta objects containing ETA information.
        """
        endpoint = self.__base_url + f"parades/{stop_code}"
        response = requests.get(endpoint, params=self.__default_params, timeout=10)
        response.raise_for_status()

        data = EtaResponseBus.model_validate(response.json())

        # Show ETA for the specified line only
        if line is not None:
            for stop in data.stops:
                stop.line_routes = [
                    route
                    for route in stop.line_routes
                    if route.line_name.lower() == line.lower()
                ]

        return [
            BusEta(
                line_code=route.line_code,
                line_name=route.line_name,
                destination=route.destination,
                eta_minutes=(bus.arrival_time - time() * 1000) // 60000,
                stop_code=stop.stop_code,
                ramp_status=(
                    bus.info.accessibility.ramp_status
                    if bus.info and bus.info.accessibility
                    else None
                ),
            )
            for stop in data.stops
            for route in stop.line_routes
            for bus in route.upcoming_buses
        ]
