# face2parselab

A clean, standalone pipeline that converts FACE UDDL data models (`.face` / `.skayl`) 
into [parseLab](https://github.com/lmco/parselab)-compatible JSON — with no dependency 
on the MUDDL toolchain, no .NET runtime, and no proprietary tools required.

[![Launch in Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/YOUR_USERNAME/face2parselab/HEAD?labpath=demo.ipynb)

---

## What this does

Takes a FACE UDDL model as input:

```
UCI_2_5.skayl + UCI_2_5.face
```

Produces parseLab-ready JSON as output:

```json
{
    "structs": [ ... ],
    "protocol_types": [
        {
            "name": "navigationcommandmdt",
            "fields": [ ... ]
        }
    ]
}
```

One command. No custom scripts per message set.

---

## Quick start

```bash
pip install pyyaml
python -m face2parselab run config.yaml
```

**Example config (`config.yaml`):**

```yaml
model:
  skayl: data/models/UCI_2_5.skayl
  face:  data/models/UCI_2_5.face

output:
  dir: output/json
  bundle: false       # true = one combined file, false = one per message

messages:
  filter: endswith    # endswith | startswith | contains | all
  value: "MDT"
```

Or select specific messages:

```yaml
messages:
  explicit:
    - NavigationCommandMDT
    - MissionPlanMDT
    - SystemStatusMDT
```

---

## Validation

Output was validated against 722 pre-generated reference JSON files produced by 
the MUDDL toolchain. Result: **722/722 messages, 0 field-level mismatches.**

| Metric | Result |
|--------|--------|
| Messages validated | 722 |
| Struct count matches | 722 / 722 |
| Field-level matches | 722 / 722 |
| Mismatches | 0 |

---

## Architecture

```
.face / .skayl  ──►  FaceReader  ──►  Protocol (IR)  ──►  ParseLabExporter  ──►  JSON
                         │                  │
                    (model-specific)   (format-agnostic)
```

The intermediate representation (`Protocol`, `Struct`, `Field`) is intentionally 
agnostic — a new reader for XSD, Proto, or any other model format plugs in without 
touching the exporter. A new exporter for any parser generator plugs in without 
touching the readers.

**Source files:**

| File | Purpose |
|------|---------|
| `face2parselab/model.py` | Agnostic IR dataclasses |
| `face2parselab/reader_face.py` | FACE .skayl/.face reader |
| `face2parselab/exporter_parselab.py` | parseLab JSON exporter |
| `face2parselab/__main__.py` | CLI + YAML manifest runner |

---

## Interactive demo

Click the Binder badge above to run the full pipeline interactively in your browser —
no installation required.

---

*Built as part of the SOSA C2 pipeline automation effort (DARPA-funded).*
