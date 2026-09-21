from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.builders import build_poc3_facts
from app.mapping import OntologyMapper


def main() -> int:
    parser = argparse.ArgumentParser(description="PoC3 Form -> Fact -> PIPA RDF demo")
    parser.add_argument("form", nargs="?", default="examples/SC-D01_form.json")
    parser.add_argument("--output-dir", default="generated")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    form_path = Path(args.form)
    if not form_path.is_absolute():
        form_path = base / form_path
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = base / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    form = json.loads(form_path.read_text(encoding="utf-8"))
    facts = build_poc3_facts(form)
    controller = form["controller"]
    mapper = OntologyMapper(
        form.get("analysis_id", "analysis"),
        controller_id=controller["controller_id"],
        controller_name=controller.get("name"),
    )
    result = mapper.map(facts)

    facts_path = output_dir / "SC-D01_facts.json"
    metadata_path = output_dir / "SC-D01_system_metadata.json"
    turtle_path = output_dir / "SC-D01_mapped.ttl"
    facts_path.write_text(json.dumps(result.facts, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata_path.write_text(
        json.dumps(result.system_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    result.serialize(str(turtle_path))

    print(f"PASS facts: {len(result.facts)} -> {facts_path}")
    print(f"PASS RDF triples: {len(result.graph)} -> {turtle_path}")
    print(f"PASS system metadata: {len(result.system_metadata)} -> {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

