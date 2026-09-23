# Rule Engine ↔ Fact Dictionary v1.0 Freeze Alignment

Date: 2026-09-23

## Scope

This change is limited to the deterministic P0 Rule Engine path. It does **not**
modify `ontology/PIPA_Ontology_v1.0.ttl` or the Fact-to-Ontology mapper.

Source contract:

- PIPA Fact Dictionary v1.0 (Freeze), 2026-09-08
- PIPA Rule Specification v1.0 Freeze summary in `docs/P0_RULE_MATRIX.md`
- Rule ↔ Fact coverage in `rules/p0_rules.json`

## Alignment changes

1. **Fact envelopes can now reach the Rule Engine.**
   - `evaluate_graph(..., facts=...)` validates the frozen `fact-1.0` envelope.
   - `evaluate_mapping_result(mapping_result, ...)` consumes the mapper's RDF
     graph and normalized Facts together.
   - This preserves `confirmed / unknown / absent` across the RDF boundary.

2. **Frozen Rule ↔ Fact coverage is enforced in strict Fact mode.**
   - Missing required Fact envelope: `AMBER` (input contract incomplete).
   - Required Fact `unknown`: `AMBER`.
   - Required Fact `absent`: `RED` for an applicable rule when the required
     combination is explicitly absent.
   - `false` remains a confirmed value and is never treated as unknown.
   - P1-R02 keeps its frozen OR semantics: confirmed retention period **or**
     confirmed identifiable end condition is sufficient when the other Fact is
     explicitly absent/unknown.

3. **Graph-level checks now match the frozen Fact value semantics more closely.**
   - P1-R01 requires a concrete purpose description, not only a `hasPurpose`
     edge.
   - P1-R03 requires concrete recipient name, PI item name, and purpose
     description, not only relation edges.
   - P2-R01 requires concrete F2-02 affected-item names.
   - P3-R04 now consumes F3-03 (`hasConsentRequest`) as frozen coverage
     requires.
   - P3-R11 now consumes F3-12 all the way to `EntrustedProcessor.hasName`.

4. **CLI strict mode.**
   - `python -m app.rules.cli <rdf.ttl> --facts <facts.json>` applies the frozen
     Fact input contract.
   - RDF-only invocation remains available as a compatibility mode, but it
     cannot distinguish `unknown` from `absent` because the mapper intentionally
     emits only confirmed assertions into RDF.

## Regression verification

Commands used in this change:

```bash
python -m pytest -q tests/test_p0_rule_engine_v2.py
# 43 passed

python -m pytest -q
# 60 passed
```

The full suite was also run with `pyshacl` available. No ontology files were
changed by this work.

## End-to-end PoC3 smoke check

`examples/SC-D01_form.json` was executed through:

`Structured Form -> build_poc3_facts -> OntologyMapper -> evaluate_mapping_result`

All eight PoC3 frozen rules returned `GREEN` with no missing or uncertain Fact
contract entries.
