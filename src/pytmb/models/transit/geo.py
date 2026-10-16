from __future__ import annotations

from typing import Annotated, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel, Field

from pytmb.models._base import ResponseModel


class CrsProperties(ResponseModel):
    name: str

    def __repr__(self):
        return f"CrsProperties(name={self.name})"

    def __str__(self):
        return self.__repr__()


class Crs(ResponseModel):
    type_: str = Field(alias="type")
    properties: CrsProperties

    def __repr__(self):
        return f"Crs(type={self.type_}, properties={self.properties})"

    def __str__(self):
        return self.__repr__()


Position: TypeAlias = tuple[float, float]
LineStringCoords: TypeAlias = list[Position]
MultiLineStringCoords: TypeAlias = list[LineStringCoords]


class LineString(ResponseModel):
    """A single line in the response CRS; EPSG:4326 positions are (longitude, latitude)."""

    type_: Literal["LineString"] = Field(alias="type")
    coordinates: LineStringCoords

    def __repr__(self) -> str:
        return "LineString(coordinates=<...>)"

    def __str__(self) -> str:
        return self.__repr__()


class MultiLineString(ResponseModel):
    """Multiple lines in the response CRS, with one extra coordinate nesting level."""

    type_: Literal["MultiLineString"] = Field(alias="type")
    coordinates: MultiLineStringCoords

    def __repr__(self) -> str:
        return "MultiLineString(coordinates=<...>)"

    def __str__(self) -> str:
        return self.__repr__()


Geometry: TypeAlias = Annotated[LineString | MultiLineString, Field(discriminator="type_")]


P = TypeVar("P", bound=BaseModel)


class Feature(ResponseModel, Generic[P]):
    type_: str = Field(alias="type")
    id_: str = Field(alias="id")
    geometry_name: str
    geometry: Geometry
    properties: P

    def __repr__(self):
        return f"Feature(id={self.id_}, type={self.type_}, geometry_name={self.geometry_name})"

    def __str__(self):
        return self.__repr__()


class FeatureCollection(ResponseModel, Generic[P]):
    crs: Crs | None = None
    total_features: int = Field(alias="totalFeatures")
    type_: str = Field(alias="type")
    features: list[Feature[P]]
    number_matched: int | None = Field(default=None, alias="numberMatched")
    number_returned: int | None = Field(default=None, alias="numberReturned")
    timestamp: str | None = Field(default=None, alias="timeStamp")

    def __repr__(self):
        preview = [(f.id_, f.geometry.type_) for f in self.features[:3]]
        more = len(self.features) - 3
        suffix = f", +{more} more" if more > 0 else ""
        return f"FeatureCollection(total_features={self.total_features}, type={self.type_}, preview={preview}{suffix})"

    def __str__(self):
        return self.__repr__()
