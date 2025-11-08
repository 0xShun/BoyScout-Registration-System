#!/usr/bin/env python3
"""Validate a JSON request file against a JSON Schema.

Usage:
  python scripts/validate_request.py <schema-path> <request-json-path>

Exits with code 0 when valid, 1 when invalid or on error.
"""
import sys
import json
from pathlib import Path

try:
    import jsonschema
except Exception as e:
    print("Missing dependency: install with `pip install jsonschema`", file=sys.stderr)
    raise


def main():
    if len(sys.argv) != 3:
        print("Usage: validate_request.py <schema-path> <request-json-path>")
        return 2

    schema_path = Path(sys.argv[1])
    instance_path = Path(sys.argv[2])

    if not schema_path.exists():
        print(f"Schema file not found: {schema_path}")
        return 2
    if not instance_path.exists():
        print(f"Request file not found: {instance_path}")
        return 2

    schema = json.loads(schema_path.read_text())
    instance = json.loads(instance_path.read_text())

    try:
        jsonschema.validate(instance=instance, schema=schema)
        print("VALID: request conforms to schema")
        return 0
    except jsonschema.ValidationError as e:
        print("INVALID: schema validation failed:")
        print(e.message)
        # print a small context if available
        if hasattr(e, "path") and e.path:
            print("Error path:", ".".join([str(p) for p in e.path]))
        return 1
    except Exception as e:
        print("ERROR while validating:", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
