"""Build the packaged response contract from a public Garmin OpenAPI JSON file.

Usage: python scripts/update_personal_api_contract.py /path/to/openapi.json
No account access. The runtime never fetches Swagger or executes this script.
"""
import argparse
import hashlib
import json
from pathlib import Path

URL = "https://developer.garmin.com/gc-developer-program/personal/swagger-docs/"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path)
    parser.add_argument("--reviewed", required=True, help="Review date, YYYY-MM-DD")
    args = parser.parse_args()
    schema = json.loads(args.schema.read_text())
    # Keep the full response definitions, including vendor units, enums,
    # timestamps and open-ended objects. Drop example payloads, not fields.
    def compact(node):
        if isinstance(node, list):
            return [compact(item) for item in node]
        if isinstance(node, dict):
            return {key: compact(value) for key, value in node.items() if key not in {"example", "examples"}}
        return node
    contract = {"source": URL, "reviewed": args.reviewed, "api_version": schema["info"]["version"],
        "schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
        "responses": {path: compact(op["get"]["responses"]["200"].get("content", {}))
                      for path, op in schema["paths"].items()},
        "schemas": compact(schema["components"]["schemas"])}
    target = Path(__file__).resolve().parents[1] / "src/garmin_archive/personal_api_contract.json"
    target.write_text(json.dumps(contract, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {len(contract['responses'])} responses and {len(contract['schemas'])} schema definitions")


if __name__ == "__main__":
    main()
