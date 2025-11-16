from __future__ import annotations

from typing import Generic, List, Literal, Optional, Tuple, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field


class CrsProperties(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str

    def __repr__(self):
        return f"CrsProperties(name={self.name})"

    def __str__(self):
        return self.__repr__()


class Crs(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type_: str = Field(alias="type")
    properties: CrsProperties

    def __repr__(self):
        return f"Crs(type={self.type_}, properties={self.properties})"

    def __str__(self):
        return self.__repr__()


Position = Tuple[float, float]
LineStringCoords = List[Position]
MultiLineStringCoords = List[LineStringCoords]


class Geometry(BaseModel):
    """GeoJSON geometry for transit entities.

    - Conforms to the GeoJSON standard: entities include a geometry and alphanumeric properties.
    - Coordinate reference system: EPSG:4326 (WGS84).
    - Coordinate order is [longitude, latitude].
    - TMB endpoints in this library use only LineString and MultiLineString.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # The geometry objects we receive are either LineString or MultiLineString
    type_: Literal["LineString", "MultiLineString"] = Field(alias="type")
    # Positions are [lon, lat] in EPSG:4326; MultiLineString nests lists of LineStrings
    coordinates: Union[LineStringCoords, MultiLineStringCoords]

    def __repr__(self):
        return f"Geometry(type={self.type_}, coordinates=<...>)"

    def __str__(self):
        return self.__repr__()


P = TypeVar("P", bound=BaseModel)


class Feature(BaseModel, Generic[P]):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    type_: str = Field(alias="type")
    id_: str = Field(alias="id")
    geometry_name: str
    geometry: Geometry
    properties: P

    def __repr__(self):
        return f"Feature(id={self.id_}, type={self.type_}, geometry_name={self.geometry_name})"

    def __str__(self):
        return self.__repr__()


class FeatureCollection(BaseModel, Generic[P]):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    crs: Optional[Crs] = None
    totalFeatures: int
    type_: str = Field(alias="type")
    features: list[Feature[P]] = Field(default_factory=list)
    numberMatched: Optional[int] = None
    numberReturned: Optional[int] = None
    timeStamp: Optional[str] = None

    def __repr__(self):
        preview = [(f.id_, f.geometry.type_) for f in self.features[:3]]
        more = len(self.features) - 3
        suffix = f", +{more} more" if more > 0 else ""
        return f"FeatureCollection(totalFeatures={self.totalFeatures}, type={self.type_}, preview={preview}{suffix})"

    def __str__(self):
        return self.__repr__()
