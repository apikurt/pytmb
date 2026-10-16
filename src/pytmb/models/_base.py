"""Shared policies for upstream responses and library-produced domain views."""

from pydantic import BaseModel, ConfigDict


class ResponseModel(BaseModel):
    """Accept wire aliases or Python names and tolerate additional upstream fields."""

    model_config = ConfigDict(extra="ignore", validate_by_alias=True, validate_by_name=True)


class DomainModel(BaseModel):
    """Reject unexpected fields when constructing or reloading a domain view."""

    model_config = ConfigDict(extra="forbid")
