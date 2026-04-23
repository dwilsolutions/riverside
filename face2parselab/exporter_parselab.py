"""
Exporter: Protocol -> parseLab JSON format.

The parseLab protocol.json format consists of:
  - "structs": list of shared/nested type definitions
  - "protocol_types": list of top-level message definitions

Each struct/message has a "name" and a list of "fields".
Each field has "name", "type", and optionally "value" and "dependee".

This exporter knows nothing about where the Protocol came from.
"""
import json
from .model import Protocol, Struct, Field, NestedField


def export_json(protocol: Protocol, output_path: str = None) -> str:
    """
    Convert a Protocol to a parseLab JSON string.
    If output_path is given, also write to file.
    Returns the JSON string.
    """
    doc = {}

    if protocol.structs:
        doc['structs'] = [_struct_to_dict(s) for s in protocol.structs]

    doc['protocol_types'] = [_struct_to_dict(m) for m in protocol.messages]

    result = json.dumps(doc, indent=4)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(result)

    return result


def _struct_to_dict(struct: Struct) -> dict:
    is_message = False  # messages use "fields", structs use "members"
    # We'll detect which key to use based on caller context — pass both for now
    # parseLab uses "members" for structs and "fields" for protocol_types
    # We handle this at the doc level instead
    return {
        'struct_name': struct.name,
        'members': [_field_to_dict(f) for f in struct.fields if _field_to_dict(f)]
    }


def _message_to_dict(struct: Struct) -> dict:
    return {
        'name': struct.name,
        'fields': [_field_to_dict(f) for f in struct.fields if _field_to_dict(f)]
    }


def export_json(protocol: Protocol, output_path: str = None) -> str:
    """
    Convert a Protocol to a parseLab JSON string.
    If output_path is given, also write to file.
    Returns the JSON string.
    """
    doc = {}

    if protocol.structs:
        doc['structs'] = []
        for s in protocol.structs:
            members = [_field_to_dict(f) for f in s.fields]
            members = [m for m in members if m]
            if members:
                doc['structs'].append({
                    'struct_name': s.name,
                    'members': members,
                })

    doc['protocol_types'] = []
    for m in protocol.messages:
        fields = [_field_to_dict(f) for f in m.fields]
        fields = [f for f in fields if f]
        if fields:
            doc['protocol_types'].append({
                'name': m.name,
                'fields': fields,
            })

    result = json.dumps(doc, indent=4)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(result)

    return result


def _field_to_dict(f) -> dict:
    """Convert a Field or NestedField to a parseLab field dict."""
    if isinstance(f, NestedField):
        return {
            'name': f.name,
            'type': f.struct_name,
        }
    elif isinstance(f, Field):
        d = {'name': f.name, 'type': f.type}
        if f.value:
            d['value'] = f.value
        if f.dependee:
            d['dependee'] = 'true'
        return d
    return None
