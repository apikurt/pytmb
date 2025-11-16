from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from pytmb.models.TransitModels.geo import FeatureCollection


class LineProperties(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Codes and identifiers
    family_code: int = Field(alias="CODI_FAMILIA")
    line_code: int = Field(alias="CODI_LINIA")
    operator_code: Optional[str] = Field(default=None, alias="CODI_OPERADOR")
    calendar_type_code: str = Field(alias="CODI_TIPUS_CALENDARI")

    aux_line_color: str = Field(alias="COLOR_AUX_LINIA")
    line_color: str = Field(alias="COLOR_LINIA")
    line_text_color: str = Field(alias="COLOR_TEXT_LINIA")

    # Timestamps: recent responses provide single DATA field; keep legacy fields optional
    data_timestamp: Optional[str] = Field(default=None, alias="DATA")
    end_date: Optional[str | date] = Field(default=None, alias="DATA_FI")
    start_date: Optional[str | date] = Field(default=None, alias="DATA_INICI")

    line_desc: str = Field(alias="DESC_LINIA")
    calendar_type_name: str = Field(alias="NOM_TIPUS_CALENDARI")

    line_destination: str = Field(alias="DESTI_LINIA")

    family_id: Optional[int] = Field(default=None, alias="ID_FAMILIA")
    line_id: int = Field(alias="ID_LINIA")
    operator_id: int = Field(alias="ID_OPERADOR")
    calendar_type_id: Optional[int] = Field(default=None, alias="ID_TIPUS_CALENDARI")
    transport_type_id: Optional[int] = Field(default=None, alias="ID_TIPUS_TRANSPORT")
    num_packages: Optional[int] = Field(default=None, alias="NUM_PAQUETS")

    family_name: str = Field(alias="NOM_FAMILIA")
    line_name: str = Field(alias="NOM_LINIA")
    operator_name: str = Field(alias="NOM_OPERADOR")
    transport_type_name: str = Field(alias="NOM_TIPUS_TRANSPORT")

    family_order: int = Field(alias="ORDRE_FAMILIA")
    line_order: int = Field(alias="ORDRE_LINIA")
    line_origin: str = Field(alias="ORIGEN_LINIA")

    def __repr__(self):
        return (
            f"LineProperties(line_id={self.line_id}, line_code={self.line_code}, "
            f"line_name={self.line_name}, destination={self.line_destination})"
        )

    def __str__(self):
        return self.__repr__()


class LinesResponse(FeatureCollection[LineProperties]):
    pass


class LineInfo(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    line_id: int
    line_code: int
    line_name: str
    operator_name: str
    transport_type_name: str
    line_origin: str
    line_destination: str
    color: str

    def __repr__(self):
        return (
            f"LineInfo(line_id={self.line_id}, line_code={self.line_code}, "
            f"line_origin={self.line_origin}, line_destination={self.line_destination}, "
            f"line_name={self.line_name}, color={self.color})"
        )

    def __str__(self):
        return self.__repr__()
