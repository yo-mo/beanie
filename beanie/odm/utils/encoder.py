import datetime
from collections import deque
from decimal import Decimal
from enum import Enum
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
)
from pathlib import PurePath
from types import GeneratorType
from typing import Any, Callable, Dict, Type
from typing import (
    List,
)
from uuid import UUID

from bson import ObjectId
from pydantic import BaseModel
from pydantic import SecretBytes, SecretStr
from pydantic.color import Color
from pydantic.json import isoformat

ENCODERS_BY_TYPE: Dict[Type[Any], Callable[[Any], Any]] = {
    Color: str,
    datetime.date: isoformat,
    datetime.time: isoformat,
    datetime.timedelta: lambda td: td.total_seconds(),
    Decimal: float,
    deque: list,
    IPv4Address: str,
    IPv4Interface: str,
    IPv4Network: str,
    IPv6Address: str,
    IPv6Interface: str,
    IPv6Network: str,
    SecretBytes: SecretBytes.get_secret_value,
    SecretStr: SecretStr.get_secret_value,
    Enum: lambda o: o.value,
    PurePath: str,
}


class Encoder:
    def __init__(self, obj, exclude=None, by_alias=True, custom_encoders=None):
        self.object = obj
        self.exclude = exclude
        self.by_alias = by_alias
        self.custom_encoders = custom_encoders

        self.main_object_encoded = None  # TODO rename
        self.encoded_objects = {}
        self.links = {}

        if self.exclude is not None and not isinstance(self.exclude,
                                                       (set, dict)):
            self.exclude = set(self.exclude)

        self.main_object_encoded = self._encode(self.object,
                                                _is_top_level=True)
        if getattr(self.object, "get_link"):
            self.encoded_objects[0] = [{
                    "object": self.object,
                    "value": self.main_object_encoded
                }]

    def _encode(
            self,
            obj: Any,
            _recursion_level: int = 0,
            _is_top_level: bool = False
    ) -> Any:
        if getattr(obj, "get_link", None) is not None and not _is_top_level:
            link = obj.get_link()
            self.links[obj.revision_id] = link
            _recursion_level += 1
            if _recursion_level not in self.encoded_objects:
                self.encoded_objects[_recursion_level] = []
            self.encoded_objects[_recursion_level].append({
                "object": obj,
                "value": self._encode(
                    obj=obj,
                    _is_top_level=True
                )
            })
            return link
        if isinstance(obj, BaseModel):
            encoders = {}
            collection_class = getattr(obj, "Collection", None)
            if collection_class:
                encoders = vars(collection_class).get("bson_encoders",
                                                      {})  # TODO manage this
            obj_dict = {}
            for k, o in obj._iter(
                to_dict=False,
                by_alias=self.by_alias
            ):
                if k not in self.exclude:  # TODO get exclude from the class
                    obj_dict[k] = o
            return self._encode(
                obj_dict,
            )
        if isinstance(
                obj, (
                        str, int, float, ObjectId, UUID, datetime.datetime,
                        type(None))
        ):
            return obj
        if isinstance(obj, dict):
            encoded_dict = {}
            for key, value in obj.items():
                encoded_value = self._encode(
                    value,
                )
                encoded_dict[key] = encoded_value
            return encoded_dict
        if isinstance(obj, (list, set, frozenset, GeneratorType, tuple)):
            return [
                self._encode(
                    item,
                )
                for item in obj
            ]
        if self.custom_encoders:
            if type(obj) in self.custom_encoders:
                return self.custom_encoders[type(obj)](obj)
            for encoder_type, encoder in self.custom_encoders.items():
                if isinstance(obj, encoder_type):
                    return encoder(obj)
        if type(obj) in ENCODERS_BY_TYPE:
            return ENCODERS_BY_TYPE[type(obj)](obj)
        for c, encoder in ENCODERS_BY_TYPE.items():
            if isinstance(obj, c):
                return encoder(obj)

        errors: List[Exception] = []
        try:
            data = dict(obj)
        except Exception as e:
            errors.append(e)
            try:
                data = vars(obj)
            except Exception as e:
                errors.append(e)
                raise ValueError(errors)
        return self._encode(
            data,
        )
