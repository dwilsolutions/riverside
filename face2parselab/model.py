"""
Intermediate representation - agnostic of source model format and target output format.
Any model reader produces a Protocol object. Any exporter consumes a Protocol object.
"""
from dataclasses import dataclass, field


@dataclass
class Field:
    name: str
    type: str           # normalized parseLab primitive: U8, U32, I32, U64, I64, D8, F32, enum
    value: str = ""     # constraint expression e.g. "(0, 255)", "0|1|2", "[a,b,c]"
    dependee: bool = False  # true if this field is a length field for a variable array
    optional: bool = False
    upper_bound: int = 1
    lower_bound: int = 1


@dataclass
class Struct:
    name: str
    fields: list = field(default_factory=list)  # list[Field | NestedField]


@dataclass
class NestedField:
    """A field whose type is another Struct (foreign reference)."""
    name: str
    struct_name: str    # name of the referenced Struct
    optional: bool = False
    upper_bound: int = 1
    lower_bound: int = 1


@dataclass
class Protocol:
    structs: list = field(default_factory=list)   # list[Struct] - shared/nested types
    messages: list = field(default_factory=list)  # list[Struct] - top-level message types
