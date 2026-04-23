"""
Reader for FACE UDDL model files (.face + .skayl).

Key facts about the UCI model structure:
- .skayl file contains: platform:View (structs), platform types, enumerations, constraints
- .face file contains: uop:Template definitions (message names)
- Every MDT template name has a matching platform:View of the same name in .skayl
- Constraints are separate elements linked by xmi:id from platform type elements
- Enumerations store their literals as direct children

Produces a Protocol object agnostic of any downstream format.
"""
import xml.etree.ElementTree as ET
from .model import Protocol, Struct, Field, NestedField

XMI = '{http://www.omg.org/XMI}'

PRIMITIVE_MAP = {
    'Boolean':       'U8',
    'Octet':         'U8',
    'Char':          'U8',
    'Short':         'I32',
    'Long':          'I32',
    'LongLong':      'I64',
    'UShort':        'U32',
    'ULong':         'U32',
    'ULongLong':     'U64',
    'Float':         'F32',
    'Double':        'D8',
    'Fixed':         'U32',
    'String':        'U8[',
    'BoundedString': 'U8[',
    'CharArray':     'U8[',
    'Sequence':      'U8[',
    'Array':         'U8[',
    'Enumeration':   'enum',
}

RESERVED = {'name','structs','fields','type','protocol_types','value','dependee','i8','i16'}

NUM_WORDS = {
    '0':'zero','1':'one','2':'two','3':'three','4':'four',
    '5':'five','6':'six','7':'seven','8':'eight','9':'nine'
}


def _safe_name(name: str) -> str:
    result = name.replace('_', '')
    for k, v in NUM_WORDS.items():
        result = result.replace(k, v)
    result = result.lower()
    if result in RESERVED:
        result += 'x'
    return result


class FaceReader:
    def __init__(self, skayl_path: str, face_path: str):
        self.skayl_path = skayl_path
        self.face_path = face_path
        self._constraints = {}
        self._platform_types = {}
        self._views = {}
        self._view_by_name = {}

    def read(self, message_filter=None) -> Protocol:
        print("  Parsing skayl...")
        self._parse_skayl()
        print(f"  Indexed {len(self._platform_types)} types, {len(self._views)} views")

        print("  Loading template names from face...")
        template_names = self._load_template_names(message_filter)
        print(f"  {len(template_names)} messages selected")

        print("  Building structs...")
        all_structs = self._build_all_structs()

        print("  Resolving messages...")
        messages = self._resolve_messages(template_names, all_structs)

        print("  Pruning unused structs...")
        used_structs = self._prune_and_order(messages, all_structs)

        return Protocol(structs=used_structs, messages=messages)

    def _parse_skayl(self):
        tree = ET.parse(self.skayl_path)
        root = tree.getroot()

        for elem in root.iter():
            xtype = elem.get(f'{XMI}type', '')
            xid = elem.get(f'{XMI}id', '')
            if not xid:
                continue

            if xtype == 'platform:IntegerRangeConstraint':
                lb = elem.get('lowerBound', '919')
                ub = elem.get('upperBound', '919')
                # 919 is the sentinel meaning "unbounded" - store both bounds raw
                # We resolve the actual value string later when we know the platform type
                if lb != '919' or ub != '919':
                    self._constraints[xid] = (lb, ub)  # tuple of raw bounds
                else:
                    self._constraints[xid] = None  # both unbounded

            elif xtype in ('platform:RealRangeConstraint', 'platform:RegularExpressionConstraint'):
                self._constraints[xid] = None

        for elem in root.iter():
            xtype = elem.get(f'{XMI}type', '')
            xid = elem.get(f'{XMI}id', '')
            if not xid or not xtype.startswith('platform:'):
                continue

            base = xtype.split(':')[-1]
            primitive = PRIMITIVE_MAP.get(base)
            if primitive is None:
                continue

            value = ''
            if primitive == 'enum':  # parseLab uses U32 + value string for enums
                literals = [c for c in elem if c.get(f'{XMI}type') == 'platform:EnumerationLiteral']
                if literals:
                    value = '|'.join(str(i) for i in range(len(literals)))
            elif primitive not in ('U8[', 'D8', 'F32'):
                TYPE_BOUNDS = {
                    'U8':  ('0', '255'),
                    'I32': ('-2147483648', '2147483647'),
                    'I64': ('-9223372036854775808', '9223372036854775807'),
                    'U32': ('0', '4294967295'),
                    'U64': ('0', '18446744073709551615'),
                }
                cid = elem.get('constraint', '')
                if cid and self._constraints.get(cid) is not None:
                    raw_lb, raw_ub = self._constraints[cid]
                    out_type = 'U32' if primitive == 'enum' else primitive
                    type_min, type_max = TYPE_BOUNDS.get(out_type, ('0', '4294967295'))
                    lb = type_min if raw_lb == '919' else raw_lb
                    ub = type_max if raw_ub == '919' else raw_ub
                    value = f'({lb}, {ub})'
                else:
                    value = ''  # no constraint or both unbounded

            self._platform_types[xid] = {'primitive': primitive, 'value': value}

        for elem in root.iter():
            if elem.get(f'{XMI}type') != 'platform:View':
                continue
            xid = elem.get(f'{XMI}id', '')
            name = elem.get('name', '')
            if not xid or not name:
                continue

            chars = []
            for child in elem:
                if child.get(f'{XMI}type') != 'platform:CharacteristicProjection':
                    continue
                chars.append({
                    'rolename':      child.get('rolename', ''),
                    'platformType':  child.get('platformType', ''),
                    'viewType':      child.get('viewType', ''),
                    'attributeKind': child.get('attributeKind', ''),
                    'optional':      child.get('optional', 'false') == 'true',
                    'lowerBound':    int(child.get('lowerBound', '1')),
                    'upperBound':    int(child.get('upperBound', '1')),
                })

            self._views[xid] = {'name': name, 'chars': chars}
            self._view_by_name[name] = xid

    def _load_template_names(self, message_filter) -> list:
        tree = ET.parse(self.face_path)
        root = tree.getroot()
        names = []
        for elem in root.iter():
            if elem.get(f'{XMI}type') == 'uop:Template':
                name = elem.get('name', '')
                if name and (message_filter is None or message_filter(name)):
                    names.append(name)
        return names

    def _build_all_structs(self) -> dict:
        structs = {}
        for xid, view in self._views.items():
            safe = _safe_name(view['name'])
            structs[safe] = self._view_to_struct(view)
        return structs

    def _view_to_struct(self, view: dict) -> Struct:
        safe_name = _safe_name(view['name'])
        fields = []

        for char in view['chars']:
            rolename = char['rolename']
            if not rolename:
                continue

            safe_role = _safe_name(rolename)
            optional = char['optional']
            lb = char['lowerBound']
            ub = char['upperBound']

            if char['attributeKind'] == 'foreignReference' and char['viewType']:
                ref_view = self._views.get(char['viewType'], {})
                ref_safe = _safe_name(ref_view.get('name', char['viewType']))

                # Only add nested field if referenced struct has content
                ref_view_data = self._views.get(char["viewType"], {})
                if ref_view_data.get("chars"):
                    fields.append(NestedField(
                        name=safe_role,
                        struct_name=ref_safe,
                        optional=optional,
                        upper_bound=ub,
                        lower_bound=lb,
                    ))
            else:
                pt_info = self._platform_types.get(char['platformType'], {})
                primitive = pt_info.get('primitive', 'U32')
                value = pt_info.get('value', '')

                if primitive == 'U8[':
                    len_name = safe_role + 'length'
                    fields.append(Field(name=len_name, type='U32', dependee=True))
                    fields.append(Field(name=safe_role, type=f'U8[{len_name}]'))
                else:
                    # parseLab represents enums as U32 with a pipe-separated value string
                    out_type = 'U32' if primitive == 'enum' else primitive
                    fields.append(Field(
                        name=safe_role, type=out_type, value=value,
                        optional=optional, upper_bound=ub, lower_bound=lb,
                    ))

        return Struct(name=safe_name, fields=fields)

    def _resolve_messages(self, template_names: list, all_structs: dict) -> list:
        messages = []
        for name in template_names:
            safe = _safe_name(name)
            if safe in all_structs:
                messages.append(all_structs[safe])
            else:
                print(f"  Warning: no View for template '{name}'")
        return messages

    def _prune_and_order(self, messages: list, all_structs: dict) -> list:
        needed = set()

        def collect(struct: Struct):
            if struct.name in needed:
                return
            needed.add(struct.name)
            for f in struct.fields:
                if isinstance(f, NestedField) and f.struct_name in all_structs:
                    collect(all_structs[f.struct_name])

        for msg in messages:
            collect(msg)

        ordered = []
        visited = set()

        def add(struct: Struct):
            if struct.name in visited:
                return
            visited.add(struct.name)
            for f in struct.fields:
                if isinstance(f, NestedField) and f.struct_name in all_structs:
                    add(all_structs[f.struct_name])
            ordered.append(struct)

        message_names = {m.name for m in messages}
        for name in needed:
            if name not in message_names and name in all_structs:
                add(all_structs[name])

        return ordered
