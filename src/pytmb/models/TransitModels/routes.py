from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from pytmb.models.TransitModels.geo import FeatureCollection


class BusRouteProperties(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    route_id: int = Field(alias="ID_RECORREGUT")
    line_id: int = Field(alias="ID_LINIA")
    line_code: int = Field(alias="CODI_LINIA")
    line_name: str = Field(alias="NOM_LINIA")
    line_desc: str = Field(alias="DESC_LINIA")

    origin_name: str = Field(alias="ORIGEN_SENTIT")
    destination_name: str = Field(alias="DESTI_SENTIT")

    line_order: int = Field(alias="ORDRE_LINIA")

    operator_id: int = Field(alias="ID_OPERADOR")
    operator_name: str = Field(alias="NOM_OPERADOR")

    family_code: int = Field(alias="CODI_FAMILIA")
    family_name: str = Field(alias="NOM_FAMILIA")
    family_order: int = Field(alias="ORDRE_FAMILIA")

    day_type_id: int = Field(alias="ID_TIPUS_DIA")
    day_type_emulated_id: int = Field(alias="ID_TIPUS_DIA_EMULAT")
    day_type_name: str = Field(alias="NOM_TIPUS_DIA")

    direction_id: int = Field(alias="ID_SENTIT")
    direction_code: str = Field(alias="SENTIT")
    direction_desc: str = Field(alias="DESC_SENTIT")

    route_type_id: int = Field(alias="ID_TIPUS_RECORREGUT")
    route_type_desc: str = Field(alias="DESC_TIPUS_RECORREGUT")

    service_type_id: int = Field(alias="ID_TIPUS_SERVEI")
    service_type_desc: str = Field(alias="DESC_SERVEI")

    sub_service_type_id: int = Field(alias="ID_TIPUS_SUB_SERVEI")
    sub_service_type_desc: str = Field(alias="DESC_SUB_SERVEI")

    start_date: Optional[str] = Field(default=None, alias="DATA_INICI")
    end_date: Optional[str] = Field(default=None, alias="DATA_FI")

    route_color: str = Field(alias="COLOR_REC")
    length_meters: float = Field(alias="LONGITUD")
    bus_lane_length_meters: float = Field(alias="LONGITUD_CARRIL_BUS")
    route_desc: Optional[str] = Field(default=None, alias="DESC_REC")

    def __repr__(self):
        return (
            f"BusRouteProperties(route_id={self.route_id}, line_code={self.line_code}, "
            f"origin={self.origin_name} -> {self.destination_name})"
        )

    def __str__(self):
        return self.__repr__()


class BusRoutesResponse(FeatureCollection[BusRouteProperties]):
    pass


class BusRoutesConsolidatedResponse(FeatureCollection[BusRouteProperties]):
    pass


class BusRouteInfo(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    route_id: int
    line_code: int
    origin_name: str
    destination_name: str
    route_color: str

    def __repr__(self):
        return (
            f"BusRouteInfo(route_id={self.route_id}, line_code={self.line_code}, "
            f"origin={self.origin_name}, destination={self.destination_name})"
        )

    def __str__(self):
        return self.__repr__()
