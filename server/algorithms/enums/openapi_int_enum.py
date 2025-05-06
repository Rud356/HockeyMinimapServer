import inspect
from enum import IntEnum

from pydantic import BaseModel, GetJsonSchemaHandler
from pydantic_core import CoreSchema


class OpenAPIIntEnum(IntEnum):
    """Document names and values for IntEnum."""

    def __new__(cls, value, doc=None):
        """Add docstrings to attributes."""
        self = int.__new__(cls, value)
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler):
        json_schema = BaseModel.__get_pydantic_json_schema__(core_schema, handler)
        json_schema["x-enum-varnames"] = [v.name for v in cls]  # Does not work with Swagger.
        json_schema["oneOf"] = [
            {"title": v.name, "const": v.value, "description": inspect.getdoc(v)} for v in cls
        ]  # For OpenAPI 3.1
        json_schema = handler.resolve_ref_schema(json_schema)
        return json_schema
