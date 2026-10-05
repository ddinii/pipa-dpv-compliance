# PoC1 Frozen Rules

## Scope

PoC1 has exactly 6 frozen P0 Rules:

- P1-R01
- P1-R02
- P1-R03
- P1-R04
- P1-R06
- P1-R07

Do not add, remove, rename, or reinterpret these rules.

## Required Facts

### P1-R01 — 처리목적 명시

Required Facts:

- F1-01
- F1-02

### P1-R02 — 처리·보유기간 명시

Required Facts:

- F1-03
- F1-04

### P1-R03 — 제3자 제공 기재

Required Facts:

- F1-05
- F1-06
- F1-07

### P1-R04 — 파기 절차·방법 기재

Required Facts:

- F1-08

### P1-R06 — 처리위탁 기재

Required Facts:

- F1-09
- F1-10

### P1-R07 — 정보주체 권리행사 방법

Required Facts:

- F1-11
- F1-12

## Rule Authority

Authoritative machine-readable metadata is:

rules/p0_rules.json

Authoritative deterministic evaluation is:

app/rules/engine.py

Do not reproduce legal evaluation logic inside an extractor, API route, or frontend.

## LLM Boundary

An LLM extractor may identify and structure F1 Facts from policy text.

It must not:

- assign GREEN/YELLOW/RED/N/A;
- replace P0RuleEngine;
- invent legal thresholds;
- create new Rule IDs;
- create new Fact IDs;
- claim final legal compliance.

Rule evaluation remains deterministic.
