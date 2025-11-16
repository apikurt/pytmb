from typing import Literal

import requests

from pytmb.models.enums import TransitType
from pytmb.models.TransitModels.lines import TransitLineInfo, TransitLinesResponse


class TransitClient:
    def __init__(self, app_id: str = None, app_key: str = None):
        if app_id is None or app_key is None:
            raise ValueError("app_id and app_key must be provided")
        self.__app_id = app_id
        self.__app_key = app_key
        self.__base_url = "https://api.tmb.cat/v1/transit/"
        self.__default_params = {"app_id": self.__app_id, "app_key": self.__app_key}

    def get_transit_lines(self, transit_type: TransitType | Literal["bus", "metro"]) -> list[TransitLineInfo]:
        """Get the list of available bus or metro lines.

        Returns:
            list[TransitLineInfo]: List of bus or metro lines.

        Details: https://developer.tmb.cat/api-docs/v1/transit#tag/Linies
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
        response = requests.get(endpoint, params=self.__default_params, timeout=10)
        response.raise_for_status()

        data = TransitLinesResponse.model_validate(response.json())

        return [
            TransitLineInfo(
                line_id=feature.properties.line_id,
                line_code=feature.properties.line_code,
                line_name=feature.properties.line_name,
                operator_name=feature.properties.operator_name,
                transport_type_name=feature.properties.transport_type_name,
                line_origin=feature.properties.line_origin,
                line_destination=feature.properties.line_destination,
                color=feature.properties.line_color,
            )
            for feature in data.features
        ]
