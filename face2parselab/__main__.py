"""
face2parselab CLI

Usage:
    python -m face2parselab run config.yaml
    python -m face2parselab run config.yaml --dry-run

Config format (YAML):
    model:
      skayl: path/to/model.skayl
      face:  path/to/model.face      # optional

    output:
      dir: output/json
      bundle: false                  # true = one combined file, false = one per message

    messages:
      filter: endswith               # endswith | startswith | contains | all
      value: "MDT"                   # the string to match against
      # OR
      explicit:                      # explicit list of message names
        - NavigationCommandMDT
        - MissionPlanMDT
"""
import argparse
import json
import os
import sys

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .reader_face import FaceReader
from .exporter_parselab import export_json


def load_config(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    with open(path) as f:
        if ext in ('.yaml', '.yml'):
            if not HAS_YAML:
                print("PyYAML not installed. Install with: pip install pyyaml")
                sys.exit(1)
            return yaml.safe_load(f)
        elif ext == '.json':
            return json.load(f)
        else:
            print(f"Unsupported config format: {ext}. Use .yaml or .json")
            sys.exit(1)


def build_filter(msg_config: dict):
    """Build a message filter function from config."""
    if not msg_config:
        return None

    explicit = msg_config.get('explicit')
    if explicit:
        names = set(explicit)
        return lambda name: name in names

    filter_type = msg_config.get('filter', 'all')
    value = msg_config.get('value', '')

    if filter_type == 'endswith':
        return lambda name: name.endswith(value)
    elif filter_type == 'startswith':
        return lambda name: name.startswith(value)
    elif filter_type == 'contains':
        return lambda name: value in name
    else:
        return None  # all


def run(config_path: str, dry_run: bool = False):
    config = load_config(config_path)

    model_cfg = config.get('model', {})
    skayl_path = model_cfg.get('skayl')
    face_path = model_cfg.get('face')

    if not skayl_path:
        print("Error: 'model.skayl' is required in config")
        sys.exit(1)

    output_cfg = config.get('output', {})
    output_dir = output_cfg.get('dir', 'output')
    bundle = output_cfg.get('bundle', False)

    msg_filter = build_filter(config.get('messages'))

    print(f"Reading model: {skayl_path}")
    reader = FaceReader(skayl_path=skayl_path, face_path=face_path)
    protocol = reader.read(message_filter=msg_filter)

    print(f"Found {len(protocol.messages)} messages, {len(protocol.structs)} supporting structs")

    if dry_run:
        print("[dry-run] Would write to:", output_dir)
        for m in protocol.messages:
            print(f"  - {m.name}")
        return

    os.makedirs(output_dir, exist_ok=True)

    if bundle:
        out_path = os.path.join(output_dir, 'protocol.json')
        export_json(protocol, out_path)
        print(f"Wrote combined: {out_path}")
    else:
        from .model import Protocol
        for msg in protocol.messages:
            single = Protocol(
                structs=protocol.structs,  # include all supporting structs for each message
                messages=[msg]
            )
            out_path = os.path.join(output_dir, f'{msg.name}.json')
            export_json(single, out_path)
        print(f"Wrote {len(protocol.messages)} files to {output_dir}/")


def main():
    parser = argparse.ArgumentParser(
        prog='face2parselab',
        description='Convert FACE UDDL models to parseLab JSON'
    )
    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run', help='Run conversion from a config file')
    run_parser.add_argument('config', help='Path to YAML or JSON config file')
    run_parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without writing files')

    args = parser.parse_args()

    if args.command == 'run':
        run(args.config, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
