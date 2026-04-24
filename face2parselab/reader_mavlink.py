"""
Reader for MAVLink message definition XML files (.xml).

MAVLink defines messages in a public XML format at mavlink.io.
This reader converts those definitions into the same Protocol IR
as the FACE reader — demonstrating the architecture is model-agnostic.

Produces a Protocol object identical in structure to FaceReader output.
"""
import xml.etree.ElementTree as ET
from .model import Protocol, Struct, Field

# MAVLink C types -> parseLab primitives
MAVLINK_TYPE_MAP = {
    'uint8_t':   'U8',
    'int8_t':    'U8',
    'uint16_t':  'U32',
    'int16_t':   'I32',
    'uint32_t':  'U32',
    'int32_t':   'I32',
    'uint64_t':  'U64',
    'int64_t':   'I64',
    'float':     'F32',
    'double':    'D8',
    'char':      'U8',
}

RESERVED = {'name','structs','fields','type','protocol_types','value','dependee','i8','i16'}

def _safe_name(name: str) -> str:
    result = name.replace('_', '').lower()
    if result in RESERVED:
        result += 'x'
    return result


class MAVLinkReader:
    """
    Reads a MAVLink common.xml (or subset) and produces a Protocol.
    Same interface as FaceReader — same IR output.
    """

    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self._enums: dict = {}   # enum_name -> list of values (0|1|2...)

    def read(self, message_filter=None) -> Protocol:
        tree = ET.parse(self.xml_path)
        root = tree.getroot()

        # Index enumerations
        self._index_enums(root)

        # Build message structs
        messages = []
        for msg_elem in root.findall('.//messages/message'):
            name = msg_elem.get('name', '')
            if message_filter and not message_filter(name):
                continue
            struct = self._message_to_struct(msg_elem)
            messages.append(struct)

        # MAVLink has no shared nested structs (all fields are primitive)
        return Protocol(structs=[], messages=messages)

    def _index_enums(self, root: ET.Element):
        for enum in root.findall('.//enums/enum'):
            name = enum.get('name', '')
            entries = enum.findall('entry')
            if entries:
                # Use sequential indices like parseLab expects
                self._enums[name] = '|'.join(str(i) for i in range(len(entries)))

    def _message_to_struct(self, msg_elem: ET.Element) -> Struct:
        name = _safe_name(msg_elem.get('name', ''))
        fields = []

        for field_elem in msg_elem.findall('field'):
            field_name = field_elem.get('name', '')
            field_type = field_elem.get('type', '')
            enum_ref   = field_elem.get('enum', '')

            safe_fname = _safe_name(field_name)

            # Handle fixed-length char arrays e.g. char[16]
            if '[' in field_type:
                base_type, size = field_type.rstrip(']').split('[')
                if base_type in ('char', 'uint8_t'):
                    # Fixed array — emit as U8[ with a dependee length field
                    len_name = safe_fname + 'length'
                    fields.append(Field(name=len_name, type='U32', dependee=True))
                    fields.append(Field(name=safe_fname, type=f'U8[{len_name}]'))
                continue

            # Enum field -> U32 + value string
            if enum_ref and enum_ref in self._enums:
                fields.append(Field(
                    name=safe_fname,
                    type='U32',
                    value=self._enums[enum_ref],
                ))
                continue

            # Primitive field
            primitive = MAVLINK_TYPE_MAP.get(field_type, 'U32')
            fields.append(Field(name=safe_fname, type=primitive))

        return Struct(name=name, fields=fields)
