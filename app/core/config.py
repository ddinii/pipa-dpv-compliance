from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

RULES_DIR = BASE_DIR / "rules"
ONTOLOGY_PATH = BASE_DIR / "ontology" / "PIPA_Ontology_v1.0.ttl"

PIPA_NS = "https://example.org/pipa-dpv#"
DPV_NS = "http://w3id.org/dpv#"
