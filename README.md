# face2parselab

A model-agnostic pipeline that converts structured message models into
[parseLab](https://github.com/lmco/parselab)-compatible JSON — with no dependency
on the MUDDL toolchain, no .NET runtime, and no proprietary tools required.

**Live demo:** https://dwilsolutions.github.io/riverside

---

## What this does

Takes any conformant message model as input and produces parseLab-ready JSON.
Currently supports two model formats:

| Reader | Format | Example |
|--------|--------|---------|
| `FaceReader` | FACE UDDL `.skayl` | UCI 2.5 (722 messages), MAVLink commands (FACE-modeled) |
| `MAVLinkReader` | MAVLink XML `.xml` | MAVLink common messages |

Output format:

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

---

## Live Demo

The interactive demo runs the actual Python pipeline live in your browser via Pyodide
(Python → WebAssembly). No installation required.

**https://dwilsolutions.github.io/riverside**

| Step | What it shows |
|------|--------------|
| 00 · Overview | Architecture and key numbers |
| 01 · Simple Model ⚡ | Hand-crafted FACE model — live execution |
| 02 · Format Proof ⚡ | parseLab spec verification — live, programmatic |
| 03 · MAVLink ⚡ | MAVLink XML — 6 messages — live execution + verification |
| 04 · FACE MAVLink ⚡ | MAVLink commands in FACE UDDL — same FaceReader as UCI 2.5 |
| 05 · UCI 2.5 · Live Diff | MUDDL reference fetched from GitHub, diffed field-by-field |
| 06 · Next Steps | Roadmap: DDS/IDL, CoT, parseLab integration |

Steps marked ⚡ execute live Python in your browser and download the generated JSON.

---

## Quick Start

```bash
pip install pyyaml
python -m face2parselab run config.yaml
```

**Example config (`config.yaml`):**

```yaml
model:
  skayl:     data/models/UCI_2_5.skayl
  templates: data/uci_templates.txt

output:
  dir:    output/json
  bundle: false

messages:
  filter: endswith
  value:  "MDT"
```

---

## Architecture

```
FACE .skayl  ──►  FaceReader    ─┐
                                  ├──►  Protocol (IR)  ──►  export_json()  ──►  parseLab JSON
MAVLink .xml ──►  MAVLinkReader  ─┘
                                       (format-agnostic)
```

The intermediate representation (`Protocol`, `Struct`, `Field`) is intentionally
agnostic — a new reader for any model format plugs in without touching the exporter,
and a new exporter for any parser generator plugs in without touching the readers.

**Source files:**

| File | Purpose |
|------|---------|
| `face2parselab/model.py` | Agnostic IR dataclasses |
| `face2parselab/reader_face.py` | FACE UDDL .skayl reader |
| `face2parselab/reader_mavlink.py` | MAVLink XML reader |
| `face2parselab/exporter_parselab.py` | parseLab JSON exporter |
| `face2parselab/__main__.py` | CLI + YAML manifest runner |

---

## Validation

Output validated against 722 MUDDL-generated reference JSON files for UCI 2.5.

| Metric | Result |
|--------|--------|
| Messages validated | **722 / 722** |
| Struct count matches | **722 / 722** |
| Field-level matches | **722 / 722** |
| Mismatches | **0** |

---

## Model Files

| File | Description | Size |
|------|-------------|------|
| `data/models/UCI_2_5.skayl` | UCI 2.5 FACE model | 22MB |
| `data/uci_templates.txt` | UCI 2.5 template names | 115KB |
| `data/models/mavlink/mavlink_subset.xml` | MAVLink common messages (XML) | 8KB |
| `data/models/mavlink/MAVLinkv8.skayl` | MAVLink commands (FACE UDDL) | 2.3MB |
| `data/models/mavlink/MAVLinkv8.face` | MAVLink commands templates | 2.2MB |
| `data/models/simple/simple_position.skayl` | Hand-crafted GPS demo model | 5KB |
| `data/reference_json/` | 10 MUDDL reference JSON files for validation | — |

---

*SOSA C2 pipeline automation — Riverside Research*
