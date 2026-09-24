# PoC2 Frozen Rules

## Scope

PoC2 has exactly 4 frozen P0 Rules:

- P2-R01
- P2-R02
- P2-R03
- P2-R08

## Required Facts

### P2-R01 — 유출등 사고 사실·통지문 존재 검토

Required Facts:

- F2-01
- F2-02
- F2-03

This rule does not automatically determine legal notification/reporting obligation.

Do not introduce:

- triggersNotificationObligation
- ReportingObligation
- notification/reporting thresholds

into frozen v1 P2-R01.

### P2-R02 — 통지 개인정보 항목 완전성

Required Facts:

- F2-02
- F2-04

### P2-R03 — 통지 시점·경위 기재

Required Facts:

- F2-08
- F2-09

F2-08 notice incident time is distinct from the actual incidentDate represented by F2-05.

Do not merge them.

### P2-R08 — 피해 최소화·대응·구제 정보

Required Facts:

- F2-01
- F2-10

Use the existing frozen measure-role/value contract.
Do not invent additional role values.

## Rule Authority

Machine-readable metadata:

rules/p0_rules.json

Deterministic implementation:

app/rules/engine.py

## LLM Boundary

The extractor produces F2 Facts only.

It must not:

- decide RuleResult status;
- automatically decide legal reportability;
- generate new legal thresholds;
- generate a notification notice;
- replace P0RuleEngine.
