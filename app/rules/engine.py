from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.term import Node

from app.mapping.fact_schema import validate_facts
from app.rules.metadata import load_rule_metadata
from app.rules.models import (
    Applicability,
    Evidence,
    InstanceRuleResult,
    RuleResult,
    RuleStatus,
    utc_now_iso,
)


PIPA = Namespace("https://w3id.org/pipa-compliance/ontology#")
META = Namespace("https://w3id.org/pipa-compliance/metadata#")
ROOT_DIR = Path(__file__).resolve().parents[2]
ONTOLOGY_PATH = ROOT_DIR / "ontology" / "PIPA_Ontology_v1.0.ttl"

STATUS_PRIORITY = {
    RuleStatus.RED: 3,
    RuleStatus.AMBER: 2,
    RuleStatus.GREEN: 1,
    RuleStatus.NOT_APPLICABLE: 0,
}


def _local_name(term: Node | None) -> str:
    if term is None:
        return ""
    text = str(term)
    if "#" in text:
        return text.rsplit("#", 1)[1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def _literal_value(value: Node) -> str | bool:
    if isinstance(value, Literal):
        python_value = value.toPython()
        if isinstance(python_value, bool):
            return python_value
        return str(python_value)
    return str(value)


def _as_bool(value: Node) -> bool | None:
    if isinstance(value, Literal):
        converted = value.toPython()
        if isinstance(converted, bool):
            return converted
        text = str(converted).strip().lower()
    else:
        text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


class P0RuleEngine:
    """Deterministic evaluator for the frozen 18 P0 rules.

    The engine consumes RDF facts that use ``PIPA_Ontology_v1.0.ttl``. It does
    not modify or extend the ontology. Rule metadata (including legal basis) is
    loaded from ``rules/p0_rules.json``.
    """

    def __init__(self, ontology_path: Path | str = ONTOLOGY_PATH) -> None:
        self.ontology_path = Path(ontology_path)
        self.ontology_graph = Graph().parse(self.ontology_path, format="turtle")
        self.metadata = load_rule_metadata()
        self._handlers: dict[str, Callable[[Graph], list[InstanceRuleResult]]] = {
            "P1-R01": self._p1_r01,
            "P1-R02": self._p1_r02,
            "P1-R03": self._p1_r03,
            "P1-R04": self._p1_r04,
            "P1-R06": self._p1_r06,
            "P1-R07": self._p1_r07,
            "P2-R01": self._p2_r01,
            "P2-R02": self._p2_r02,
            "P2-R03": self._p2_r03,
            "P2-R08": self._p2_r08,
            "P3-R01": self._p3_r01,
            "P3-R02": self._p3_r02,
            "P3-R03": self._p3_r03,
            "P3-R04": self._p3_r04,
            "P3-R05": self._p3_r05,
            "P3-R06": self._p3_r06,
            "P3-R08": self._p3_r08,
            "P3-R11": self._p3_r11,
        }

    def evaluate_graph(
        self,
        data_graph: Graph,
        poc: str | None = None,
        *,
        facts: Iterable[Mapping[str, Any]] | None = None,
    ) -> list[RuleResult]:
        """Evaluate the frozen rules against RDF plus the Fact input contract.

        ``facts`` is optional for backwards compatibility with legacy RDF-only
        callers.  When supplied, it is validated as a frozen ``fact-1.0``
        envelope and its ``confirmed / unknown / absent`` state is enforced
        before a graph-derived result may be treated as final.  This is the
        spec-conformant path because the Fact Dictionary defines Facts as the
        Rule Engine input contract.
        """
        graph = self._combined_graph(data_graph)
        validated_facts = validate_facts(list(facts)) if facts is not None else None
        rule_ids = [
            rule_id
            for rule_id, metadata in self.metadata.items()
            if poc is None or metadata.poc.lower() == poc.lower()
        ]
        return [
            self.evaluate_rule(
                graph,
                rule_id,
                graph_is_combined=True,
                facts=validated_facts,
                facts_are_validated=True,
            )
            for rule_id in rule_ids
        ]

    def evaluate_mapping_result(self, mapping_result: Any, poc: str | None = None) -> list[RuleResult]:
        """Evaluate an ``OntologyMapper`` result without changing the mapper.

        ``MappingResult`` already exposes both ``graph`` and normalized ``facts``.
        Keeping this adapter in the Rule Engine lets unknown/absent state survive
        the RDF boundary without adding any ontology terms.
        """
        graph = Graph()
        for triple in mapping_result.graph:
            graph.add(triple)

        # Presence is document-level technical metadata.  PoC2 incident graphs
        # are intentionally not ProcessingActivity graphs and therefore need
        # not contain a PersonalInformationController node.  Project the
        # metadata onto one stable, ephemeral document node instead of making
        # N/A depend on a domain individual that may not exist.
        metadata_subject = META.document
        predicate_by_activity_type = {
            "ThirdPartyProvision": META.thirdPartyProvisionState,
            "EntrustedProcessing": META.entrustedProcessingState,
            "NotificationNotice": META.notificationNoticeState,
        }
        for item in mapping_result.system_metadata:
            if item.get("field") != "activity_presence":
                continue
            predicate = predicate_by_activity_type.get(item.get("activity_type"))
            if predicate is None:
                continue
            graph.add((metadata_subject, predicate, Literal(str(item.get("state")))))

        return self.evaluate_graph(graph, poc=poc, facts=mapping_result.facts)

    def evaluate_rule(
        self,
        data_graph: Graph,
        rule_id: str,
        *,
        graph_is_combined: bool = False,
        facts: Iterable[Mapping[str, Any]] | None = None,
        facts_are_validated: bool = False,
    ) -> RuleResult:
        if rule_id not in self._handlers:
            raise KeyError(f"Unknown P0 rule: {rule_id}")
        graph = data_graph if graph_is_combined else self._combined_graph(data_graph)
        validated_facts = None
        if facts is not None:
            validated_facts = list(facts) if facts_are_validated else validate_facts(list(facts))

        instance_results = self._handlers[rule_id](graph)
        if validated_facts is not None:
            instance_results = self._apply_fact_input_contract(
                rule_id,
                instance_results,
                validated_facts,
            )
        return self._summarize(rule_id, instance_results)

    def _combined_graph(self, data_graph: Graph) -> Graph:
        graph = Graph()
        for triple in self.ontology_graph:
            graph.add(triple)
        for triple in data_graph:
            graph.add(triple)
        graph.bind("pipa", PIPA)
        return graph

    def _instances(self, graph: Graph, target_class: URIRef) -> list[Node]:
        classes = {target_class}
        changed = True
        while changed:
            changed = False
            for child, _, parent in graph.triples((None, RDFS.subClassOf, None)):
                if parent in classes and isinstance(child, URIRef) and child not in classes:
                    classes.add(child)
                    changed = True
        found: set[Node] = set()
        for cls in classes:
            found.update(graph.subjects(RDF.type, cls))
        return sorted(found, key=str)

    def _objects(self, graph: Graph, subject: Node, predicate: URIRef) -> list[Node]:
        return sorted(set(graph.objects(subject, predicate)), key=str)

    def _nonempty_values(self, graph: Graph, subject: Node, predicate: URIRef) -> list[Node]:
        values: list[Node] = []
        for value in self._objects(graph, subject, predicate):
            if isinstance(value, Literal):
                text = str(value).strip()
                if not text or text.lower() in {"unknown", "null", "none"}:
                    continue
            values.append(value)
        return values

    def _class_is_subclass_of(self, graph: Graph, child: URIRef, parent: URIRef) -> bool:
        frontier: list[URIRef] = [child]
        seen: set[URIRef] = set()
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            if current == parent:
                return True
            frontier.extend(
                candidate
                for candidate in graph.objects(current, RDFS.subClassOf)
                if isinstance(candidate, URIRef)
            )
        return False

    def _is_instance_of(self, graph: Graph, node: Node, target_class: URIRef) -> bool:
        for node_type in graph.objects(node, RDF.type):
            if node_type == target_class:
                return True
            if isinstance(node_type, URIRef) and self._class_is_subclass_of(graph, node_type, target_class):
                return True
        return False

    def _has_specific_legal_basis_type(self, graph: Graph, basis: Node) -> bool:
        for basis_type in graph.objects(basis, RDF.type):
            if not isinstance(basis_type, URIRef) or basis_type == PIPA.LegalBasis:
                continue
            if self._class_is_subclass_of(graph, basis_type, PIPA.LegalBasis):
                return True
        return False

    def _source_evidence(self, graph: Graph, subject: Node) -> list[Evidence]:
        evidence: list[Evidence] = []
        for value in graph.objects(subject, PIPA.hasSourceEvidence):
            evidence.append(
                Evidence(
                    evidence_type="source_text",
                    subject=str(subject),
                    predicate="hasSourceEvidence",
                    source_text=str(value),
                )
            )
        return evidence

    def _assertion_evidence(
        self,
        graph: Graph,
        subject: Node,
        predicate: URIRef,
        *,
        include_object_evidence: bool = True,
    ) -> list[Evidence]:
        evidence = self._source_evidence(graph, subject)
        for value in self._objects(graph, subject, predicate):
            evidence.append(
                Evidence(
                    evidence_type="rdf_assertion",
                    subject=str(subject),
                    predicate=_local_name(predicate),
                    value=self._evidence_value(graph, value),
                )
            )
            if include_object_evidence and isinstance(value, URIRef):
                evidence.extend(self._source_evidence(graph, value))
        return self._dedupe_evidence(evidence)

    @staticmethod
    def _evidence_value(graph: Graph, value: Node) -> str | bool:
        """Return a human-readable RDF object without changing rule matching.

        Mapper-generated resource URIs contain hashes for stable identity.  Those
        identifiers are useful internally but are not suitable as user-facing
        evidence.  Prefer the resource's Korean/declared rdfs:label when one is
        available and retain the original literal/URI only as a fallback.
        """
        if isinstance(value, URIRef):
            labels = [str(label).strip() for label in graph.objects(value, RDFS.label)]
            readable_labels = [label for label in labels if label]
            if readable_labels:
                return readable_labels[0]
        return _literal_value(value)

    def _absence_evidence(self, subject: Node | str, predicate: str, note: str) -> Evidence:
        return Evidence(
            evidence_type="absence",
            subject=str(subject),
            predicate=predicate,
            note=note,
        )

    def _fact_key(self, subject: Node, predicate: URIRef | str) -> str:
        pred_name = _local_name(predicate) if isinstance(predicate, URIRef) else predicate
        return f"rdf:{_local_name(subject)}:{pred_name}"

    @staticmethod
    def _dedupe_evidence(items: Iterable[Evidence]) -> list[Evidence]:
        unique: list[Evidence] = []
        seen: set[tuple] = set()
        for item in items:
            key = (
                item.evidence_type,
                item.subject,
                item.predicate,
                item.value,
                item.source_text,
                item.note,
            )
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _apply_fact_input_contract(
        self,
        rule_id: str,
        instance_results: list[InstanceRuleResult],
        facts: list[dict[str, Any]],
    ) -> list[InstanceRuleResult]:
        """Enforce the frozen Rule↔Fact coverage and value-state semantics.

        RDF intentionally contains confirmed assertions only.  Therefore a
        graph-only evaluator cannot distinguish an extractor that returned
        ``unknown`` from one that returned ``absent``.  The frozen Fact
        Dictionary requires that distinction at the Rule Engine boundary.

        Contract policy:
        * missing Fact envelope -> AMBER (input contract incomplete)
        * required Fact with value_state=unknown -> AMBER
        * required Fact with value_state=absent -> RED when the rule's required
          combination is explicitly absent
        * confirmed false remains a confirmed value; it is never rewritten as
          unknown/absent.

        N/A instance results are preserved because applicability has already
        been established independently by the rule handler.
        """
        required = self.metadata[rule_id].required_fact_ids
        states_by_type: dict[str, set[str]] = {fact_type: set() for fact_type in required}
        ids_by_type: dict[str, list[str]] = {fact_type: [] for fact_type in required}

        for fact in facts:
            fact_type = fact.get("fact_type")
            if fact_type not in states_by_type:
                continue
            states_by_type[fact_type].add(str(fact.get("value_state")))
            ids_by_type[fact_type].append(str(fact.get("fact_id")))

        missing_types = [fact_type for fact_type in required if not states_by_type[fact_type]]
        unknown_types = [
            fact_type
            for fact_type in required
            if "unknown" in states_by_type[fact_type]
        ]
        absent_types = [
            fact_type
            for fact_type in required
            if "absent" in states_by_type[fact_type]
        ]

        # P1-R02 is explicitly ``retention period OR identifiable end
        # condition`` in the frozen rule matrix.  F1-03 and F1-04 are both
        # consumed so that the extractor must state what it found, but one
        # confirmed alternative is sufficient.  If neither is confirmed and
        # one side remains UNKNOWN, the rule is unresolved rather than RED.
        if rule_id == "P1-R02":
            alternatives = {"F1-03", "F1-04"}
            confirmed_alternative = any(
                "confirmed" in states_by_type[fact_type]
                for fact_type in alternatives
            )
            unknown_alternative = any(
                "unknown" in states_by_type[fact_type]
                for fact_type in alternatives
            )
            if confirmed_alternative:
                unknown_types = [item for item in unknown_types if item not in alternatives]
                absent_types = [item for item in absent_types if item not in alternatives]
            elif unknown_alternative:
                # An UNKNOWN alternative can still satisfy the OR branch once
                # resolved, so explicit absence of the other branch is not a
                # conclusive RED.
                absent_types = [item for item in absent_types if item not in alternatives]

        if not (missing_types or unknown_types or absent_types):
            return instance_results

        contract_evidence: list[Evidence] = []
        for fact_type in missing_types:
            contract_evidence.append(
                Evidence(
                    evidence_type="fact_contract",
                    predicate=fact_type,
                    note="required Fact envelope missing",
                )
            )
        for fact_type in unknown_types:
            contract_evidence.append(
                Evidence(
                    evidence_type="fact_contract",
                    predicate=fact_type,
                    value="unknown",
                    note=f"Fact IDs: {', '.join(ids_by_type[fact_type])}",
                )
            )
        for fact_type in absent_types:
            contract_evidence.append(
                Evidence(
                    evidence_type="fact_contract",
                    predicate=fact_type,
                    value="absent",
                    note=f"Fact IDs: {', '.join(ids_by_type[fact_type])}",
                )
            )

        rewritten: list[InstanceRuleResult] = []
        for result in instance_results:
            if result.status == RuleStatus.NOT_APPLICABLE:
                rewritten.append(result)
                continue

            result.evidence = self._dedupe_evidence([*result.evidence, *contract_evidence])

            if absent_types:
                result.status = RuleStatus.RED
                result.applicability = (
                    result.applicability
                    if result.applicability != Applicability.UNKNOWN
                    else Applicability.TRUE
                )
                result.missing_facts = sorted(
                    set(result.missing_facts)
                    | {f"fact:{fact_type}:absent" for fact_type in absent_types}
                )
                result.reason = (
                    "Frozen Fact input contract에서 필수 Fact가 absent로 확인되었습니다. "
                    + result.reason
                )
                result.recommendation = (
                    "absent인 필수 Fact를 원문/구조화 Form 근거로 보완한 뒤 다시 평가하세요."
                )
            else:
                # Unknown and a missing Fact envelope are unresolved input
                # states.  They must not collapse to graph-level RED simply
                # because no confirmed triple was emitted by the mapper.
                result.status = RuleStatus.AMBER
                result.uncertain_facts = sorted(
                    set(result.uncertain_facts)
                    | {f"fact:{fact_type}:unknown" for fact_type in unknown_types}
                    | {f"fact:{fact_type}:missing_envelope" for fact_type in missing_types}
                )
                result.reason = (
                    "Frozen Fact input contract가 불완전하거나 UNKNOWN 상태를 포함합니다. "
                    + result.reason
                )
                result.recommendation = (
                    "필수 Fact의 value_state를 confirmed 또는 명시적 absent로 확정한 뒤 다시 평가하세요."
                )
            rewritten.append(result)

        return rewritten

    @staticmethod
    def _status_for_instances(instance_results: list[InstanceRuleResult]) -> RuleStatus:
        applicable = [r.status for r in instance_results if r.status != RuleStatus.NOT_APPLICABLE]
        if not applicable:
            return RuleStatus.NOT_APPLICABLE
        return max(applicable, key=lambda status: STATUS_PRIORITY[status])

    @staticmethod
    def _applicability_for_instances(instance_results: list[InstanceRuleResult]) -> Applicability:
        values = {r.applicability for r in instance_results}
        if Applicability.TRUE in values:
            return Applicability.TRUE
        if Applicability.UNKNOWN in values:
            return Applicability.UNKNOWN
        return Applicability.FALSE

    def _summarize(self, rule_id: str, instance_results: list[InstanceRuleResult]) -> RuleResult:
        metadata = self.metadata[rule_id]
        if not instance_results:
            instance_results = [
                InstanceRuleResult(
                    instance_id="__document__",
                    status=RuleStatus.AMBER,
                    applicability=Applicability.UNKNOWN,
                    uncertain_facts=["applicability"],
                    evidence=[
                        Evidence(
                            evidence_type="absence",
                            note="규칙 적용 여부를 판단할 대상 인스턴스를 RDF 그래프에서 확인하지 못함",
                        )
                    ],
                    reason="적용 대상의 존재 여부가 확인되지 않아 자동 판정을 확정할 수 없습니다.",
                    recommendation="Fact extraction 단계에서 적용 대상 존재/부재를 명시적으로 확인하세요.",
                )
            ]

        status = self._status_for_instances(instance_results)
        applicability = self._applicability_for_instances(instance_results)
        matched = sorted({item for r in instance_results for item in r.matched_facts})
        missing = sorted({item for r in instance_results for item in r.missing_facts})
        uncertain = sorted({item for r in instance_results for item in r.uncertain_facts})
        evidence = self._dedupe_evidence(item for r in instance_results for item in r.evidence)

        status_counts = Counter(r.status.value for r in instance_results)
        reason = (
            f"{metadata.title}: 인스턴스 {len(instance_results)}개 평가 결과 "
            + ", ".join(f"{key}={value}" for key, value in sorted(status_counts.items()))
            + f"; 대표 상태={status.value}."
        )
        recommendations = [r.recommendation for r in instance_results if r.recommendation]
        recommendation = recommendations[0] if recommendations else "추가 조치가 필요하지 않습니다."

        implementation_notes = list(metadata.notes)

        return RuleResult(
            rule_id=rule_id,
            rule_version=metadata.version,
            status=status,
            applicability=applicability,
            matched_facts=matched,
            missing_facts=missing,
            uncertain_facts=uncertain,
            evidence=evidence,
            legal_basis=list(metadata.legal_basis),
            reason=reason,
            recommendation=recommendation,
            evaluated_at=utc_now_iso(),
            instance_results=instance_results,
            implementation_notes=implementation_notes,
        )

    def _ontology_term_exists(self, local_name: str) -> bool:
        term = PIPA[local_name]
        return any(self.ontology_graph.triples((term, RDF.type, None)))

    def _explicit_state(self, graph: Graph, predicate: URIRef) -> str | None:
        for value in graph.objects(None, predicate):
            return str(value)
        return None

    def _conditional_no_targets(
        self,
        graph: Graph,
        predicate: URIRef,
        label: str,
    ) -> list[InstanceRuleResult]:
        state = self._explicit_state(graph, predicate)
        if state == "confirmed_false":
            return [
                InstanceRuleResult(
                    instance_id="__document__",
                    status=RuleStatus.NOT_APPLICABLE,
                    applicability=Applicability.FALSE,
                    matched_facts=[f"metadata:{_local_name(predicate)}=confirmed_false"],
                    reason=f"{label}가 없다고 명시적으로 확인되었습니다.",
                    recommendation="해당 없음으로 유지합니다.",
                )
            ]
        return [
            InstanceRuleResult(
                instance_id="__document__",
                status=RuleStatus.AMBER,
                applicability=Applicability.UNKNOWN,
                uncertain_facts=[label],
                evidence=[
                    Evidence(
                        evidence_type="absence",
                        predicate=label,
                        note="대상 인스턴스가 없지만 명시적 부재(confirmed_false)도 확인되지 않음",
                    )
                ],
                reason=f"{label}의 존재/부재를 확정할 수 없습니다.",
                recommendation=f"{label}의 존재 여부를 Fact로 명시하세요.",
            )
        ]

    # ------------------------------------------------------------------
    # PoC1
    # ------------------------------------------------------------------

    def _p1_r01(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._instances(graph, PIPA.CollectionAndUse)
        if not activities:
            return [
                InstanceRuleResult(
                    instance_id="__document__",
                    status=RuleStatus.RED,
                    applicability=Applicability.TRUE,
                    missing_facts=["CollectionAndUse.hasPurpose"],
                    evidence=[self._absence_evidence("__document__", "CollectionAndUse.hasPurpose", "수집·이용 목적을 확인하지 못함")],
                    reason="처리목적이 확인되지 않았습니다.",
                    recommendation="수집·이용 처리행위별 목적을 명시하세요.",
                )
            ]
        results = []
        for activity in activities:
            purposes = self._objects(graph, activity, PIPA.hasPurpose)
            evidence = self._assertion_evidence(graph, activity, PIPA.hasPurpose)
            described_purposes: list[Node] = []
            ambiguous_purposes: list[Node] = []
            for purpose in purposes:
                evidence += self._assertion_evidence(graph, purpose, PIPA.hasPurposeDescription)
                if self._nonempty_values(graph, purpose, PIPA.hasPurposeDescription):
                    described_purposes.append(purpose)
                else:
                    ambiguous_purposes.append(purpose)

            if purposes and not ambiguous_purposes:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(activity, PIPA.hasPurpose),
                            *[
                                self._fact_key(purpose, PIPA.hasPurposeDescription)
                                for purpose in described_purposes
                            ],
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="처리행위별 구체적인 처리목적이 확인됩니다.",
                        recommendation="현재 목적-처리행위 연결과 목적 설명을 유지하세요.",
                    )
                )
            elif purposes:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(activity, PIPA.hasPurpose)],
                        uncertain_facts=[
                            self._fact_key(purpose, PIPA.hasPurposeDescription)
                            for purpose in ambiguous_purposes
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="처리목적 연결은 있으나 F1-02에 해당하는 구체 목적 값이 모호합니다.",
                        recommendation="각 ProcessingPurpose에 구체적인 hasPurposeDescription을 명시하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        missing_facts=[self._fact_key(activity, PIPA.hasPurpose)],
                        evidence=[self._absence_evidence(activity, "hasPurpose", "해당 CollectionAndUse의 목적 연결이 없음")],
                        reason="처리행위별 목적이 확인되지 않았습니다.",
                        recommendation="해당 처리행위에 hasPurpose를 연결하세요.",
                    )
                )
        return results

    def _substantive_processing_activities(self, graph: Graph) -> list[Node]:
        candidates: set[Node] = set()
        for cls in (PIPA.CollectionAndUse, PIPA.ThirdPartyProvision, PIPA.CrossBorderTransfer):
            candidates.update(self._instances(graph, cls))
        return sorted(candidates, key=str)

    def _retention_complete(self, graph: Graph, activity: Node) -> tuple[bool, list[Evidence], list[str]]:
        retentions = self._objects(graph, activity, PIPA.hasRetention)
        evidence = self._assertion_evidence(graph, activity, PIPA.hasRetention)
        matched: list[str] = []
        if retentions:
            matched.append(self._fact_key(activity, PIPA.hasRetention))
        for retention in retentions:
            periods = self._objects(graph, retention, PIPA.hasRetentionPeriod)
            ends = self._objects(graph, retention, PIPA.hasRetentionEndCondition)
            if periods:
                matched.append(self._fact_key(retention, PIPA.hasRetentionPeriod))
                evidence.extend(self._assertion_evidence(graph, retention, PIPA.hasRetentionPeriod))
                for period in periods:
                    evidence.extend(self._assertion_evidence(graph, period, PIPA.hasDurationValue))
                    if self._nonempty_values(graph, period, PIPA.hasDurationValue):
                        matched.append(self._fact_key(period, PIPA.hasDurationValue))
                        return True, self._dedupe_evidence(evidence), matched
            if ends:
                matched.append(self._fact_key(retention, PIPA.hasRetentionEndCondition))
                evidence.extend(self._assertion_evidence(graph, retention, PIPA.hasRetentionEndCondition))
                for end in ends:
                    evidence.extend(self._assertion_evidence(graph, end, PIPA.hasEndConditionDescription))
                    if self._nonempty_values(graph, end, PIPA.hasEndConditionDescription):
                        matched.append(self._fact_key(end, PIPA.hasEndConditionDescription))
                        return True, self._dedupe_evidence(evidence), matched
        return False, self._dedupe_evidence(evidence), matched

    def _p1_r02(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._substantive_processing_activities(graph)
        any_retention = bool(self._instances(graph, PIPA.Retention))
        if not activities:
            return [
                InstanceRuleResult(
                    instance_id="__document__",
                    status=RuleStatus.RED,
                    applicability=Applicability.TRUE,
                    missing_facts=["PersonalInformationProcessing.hasRetention"],
                    evidence=[self._absence_evidence("__document__", "hasRetention", "처리·보유기간 구조를 확인하지 못함")],
                    reason="처리·보유기간을 확인할 처리행위가 없습니다.",
                    recommendation="처리행위별 보유기간 또는 종료조건을 구조화하세요.",
                )
            ]
        results = []
        for activity in activities:
            complete, evidence, matched = self._retention_complete(graph, activity)
            if complete:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=matched,
                        evidence=evidence,
                        reason="처리행위에 기간 또는 식별 가능한 종료조건이 연결되어 있습니다.",
                        recommendation="현재 처리행위-보유정보 연결을 유지하세요.",
                    )
                )
            elif any_retention:
                evidence = evidence or [
                    self._absence_evidence(activity, "hasRetention", "문서에는 보유정보가 있으나 해당 activity 연결을 확인하지 못함")
                ]
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        uncertain_facts=[self._fact_key(activity, PIPA.hasRetention)],
                        evidence=evidence,
                        reason="보유 관련 정보는 존재하지만 이 처리행위와의 연결이 명확하지 않습니다.",
                        recommendation="보유기간/종료조건을 해당 processing activity에 직접 연결하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        missing_facts=[self._fact_key(activity, PIPA.hasRetention)],
                        evidence=[self._absence_evidence(activity, "hasRetention", "기간·종료조건 모두 확인되지 않음")],
                        reason="기간 또는 종료조건을 확인하지 못했습니다.",
                        recommendation="해당 처리행위의 보유기간 또는 종료조건을 명시하세요.",
                    )
                )
        return results

    def _p1_r03(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._instances(graph, PIPA.ThirdPartyProvision)
        if not activities:
            return self._conditional_no_targets(graph, META.thirdPartyProvisionState, "ThirdPartyProvision")
        results = []
        required = [PIPA.hasRecipient, PIPA.hasPersonalInformation, PIPA.hasPurpose]
        for activity in activities:
            missing = [predicate for predicate in required if not self._objects(graph, activity, predicate)]
            evidence = [item for predicate in required for item in self._assertion_evidence(graph, activity, predicate)]
            ambiguous: list[tuple[Node, URIRef]] = []
            detail_requirements = (
                (PIPA.hasRecipient, PIPA.hasName),
                (PIPA.hasPersonalInformation, PIPA.hasItemName),
                (PIPA.hasPurpose, PIPA.hasPurposeDescription),
            )
            for relation, detail in detail_requirements:
                for linked in self._objects(graph, activity, relation):
                    evidence += self._assertion_evidence(graph, linked, detail)
                    if not self._nonempty_values(graph, linked, detail):
                        ambiguous.append((linked, detail))

            if not missing and not ambiguous:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(activity, predicate) for predicate in required],
                        evidence=self._dedupe_evidence(evidence),
                        reason="제3자 제공의 수령자·항목·목적이 모두 확인됩니다.",
                        recommendation="현재 제3자 제공 정보를 유지하세요.",
                    )
                )
            elif not missing:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(activity, predicate) for predicate in required],
                        uncertain_facts=[
                            self._fact_key(linked, detail) for linked, detail in ambiguous
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="제3자 제공 연결은 있으나 수령자명·항목명·목적 값 중 일부가 모호합니다.",
                        recommendation="F1-05/F1-06/F1-07에 해당하는 구체 값을 모두 명시하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(activity, p) for p in required if p not in missing],
                        missing_facts=[self._fact_key(activity, p) for p in missing],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(activity, _local_name(p), "제3자 제공 필수요소 누락") for p in missing
                        ],
                        reason="제3자 제공 필수요소가 하나 이상 누락되었습니다.",
                        recommendation="제공받는 자, 제공 항목, 제공 목적을 모두 명시하세요.",
                    )
                )
        return results

    def _p1_r04(self, graph: Graph) -> list[InstanceRuleResult]:
        destructions = self._instances(graph, PIPA.Destruction)
        if not destructions:
            return [
                InstanceRuleResult(
                    instance_id="__document__",
                    status=RuleStatus.RED,
                    applicability=Applicability.TRUE,
                    missing_facts=["Destruction.hasDestructionMethod"],
                    evidence=[self._absence_evidence("__document__", "hasDestructionMethod", "파기 방법을 확인하지 못함")],
                    reason="파기 방법이 확인되지 않았습니다.",
                    recommendation="구체적인 파기 절차·방법을 명시하세요.",
                )
            ]
        results = []
        for destruction in destructions:
            raw_methods = self._objects(graph, destruction, PIPA.hasDestructionMethod)
            methods = self._nonempty_values(graph, destruction, PIPA.hasDestructionMethod)
            evidence = self._assertion_evidence(graph, destruction, PIPA.hasDestructionMethod)
            if methods:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(destruction),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(destruction, PIPA.hasDestructionMethod)],
                        evidence=evidence,
                        reason="구체적인 파기 방법이 확인됩니다.",
                        recommendation="현재 파기 방법 명시를 유지하세요.",
                    )
                )
            elif raw_methods:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(destruction),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        uncertain_facts=[self._fact_key(destruction, PIPA.hasDestructionMethod)],
                        evidence=evidence,
                        reason="파기 방법 값이 UNKNOWN/모호하여 자동 확정할 수 없습니다.",
                        recommendation="구체적인 파기 절차·방법을 명시하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(destruction),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        missing_facts=[self._fact_key(destruction, PIPA.hasDestructionMethod)],
                        evidence=[self._absence_evidence(destruction, "hasDestructionMethod", "파기 활동에 방법이 연결되지 않음")],
                        reason="파기 활동은 있으나 파기 방법이 확인되지 않습니다.",
                        recommendation="해당 Destruction에 hasDestructionMethod를 명시하세요.",
                    )
                )
        return results

    def _p1_r06(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._instances(graph, PIPA.EntrustedProcessing)
        if not activities:
            return self._conditional_no_targets(graph, META.entrustedProcessingState, "EntrustedProcessing")
        results = []
        for activity in activities:
            processors = self._objects(graph, activity, PIPA.hasProcessor)
            raw_task = self._objects(graph, activity, PIPA.entrustedTaskText)
            task = self._nonempty_values(graph, activity, PIPA.entrustedTaskText)
            processors_missing_name: list[Node] = []
            processors_uncertain_name: list[Node] = []
            processors_with_name: list[Node] = []

            evidence = self._assertion_evidence(graph, activity, PIPA.hasProcessor)
            evidence += self._assertion_evidence(graph, activity, PIPA.entrustedTaskText)
            for processor in processors:
                raw_names = self._objects(graph, processor, PIPA.hasName)
                names = self._nonempty_values(graph, processor, PIPA.hasName)
                evidence += self._assertion_evidence(graph, processor, PIPA.hasName)
                if names:
                    processors_with_name.append(processor)
                elif raw_names:
                    processors_uncertain_name.append(processor)
                else:
                    processors_missing_name.append(processor)

            missing_facts: list[str] = []
            if not processors:
                missing_facts.append(self._fact_key(activity, PIPA.hasProcessor))
            missing_facts.extend(self._fact_key(processor, PIPA.hasName) for processor in processors_missing_name)
            if not raw_task:
                missing_facts.append(self._fact_key(activity, PIPA.entrustedTaskText))

            uncertain_facts = [self._fact_key(processor, PIPA.hasName) for processor in processors_uncertain_name]
            if raw_task and not task:
                uncertain_facts.append(self._fact_key(activity, PIPA.entrustedTaskText))

            matched_facts = []
            if processors:
                matched_facts.append(self._fact_key(activity, PIPA.hasProcessor))
            if task:
                matched_facts.append(self._fact_key(activity, PIPA.entrustedTaskText))
            matched_facts.extend(self._fact_key(processor, PIPA.hasName) for processor in processors_with_name)

            if missing_facts:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=matched_facts,
                        missing_facts=missing_facts,
                        uncertain_facts=uncertain_facts,
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(activity, fact.rsplit(":", 1)[-1], "처리위탁 필수정보 누락")
                            for fact in missing_facts
                        ],
                        reason="수탁자명 또는 위탁업무 정보가 누락되었습니다.",
                        recommendation="각 수탁자명과 위탁업무 내용을 모두 명시하세요.",
                    )
                )
            elif uncertain_facts:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=matched_facts,
                        uncertain_facts=uncertain_facts,
                        evidence=self._dedupe_evidence(evidence),
                        reason="수탁자명 또는 위탁업무 값이 UNKNOWN/모호하여 자동 확정할 수 없습니다.",
                        recommendation="각 수탁자명과 위탁업무 내용을 구체적으로 명시하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=matched_facts,
                        evidence=self._dedupe_evidence(evidence),
                        reason="각 수탁자명과 위탁업무가 확인됩니다.",
                        recommendation="현재 위탁 정보 명시를 유지하세요.",
                    )
                )
        return results

    def _p1_r07(self, graph: Graph) -> list[InstanceRuleResult]:
        subjects = self._instances(graph, PIPA.DataSubject)
        if not subjects:
            return [
                InstanceRuleResult(
                    instance_id="__document__",
                    status=RuleStatus.RED,
                    applicability=Applicability.TRUE,
                    missing_facts=["DataSubject.hasRight", "DataSubjectRight.hasExerciseProcedure"],
                    evidence=[self._absence_evidence("__document__", "hasRight/hasExerciseProcedure", "권리 및 행사절차를 확인하지 못함")],
                    reason="정보주체 권리행사 방법·절차가 확인되지 않습니다.",
                    recommendation="권리 종류와 행사 방법·절차를 명시하세요.",
                )
            ]

        results = []
        for subject in subjects:
            rights = self._objects(graph, subject, PIPA.hasRight)
            evidence = self._assertion_evidence(graph, subject, PIPA.hasRight)

            if not rights:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(subject),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        missing_facts=[self._fact_key(subject, PIPA.hasRight)],
                        evidence=[self._absence_evidence(subject, "hasRight", "권리행사 정보 미기재")],
                        reason="권리행사 방법·절차가 확인되지 않습니다.",
                        recommendation="권리 종류와 행사 방법을 명시하세요.",
                    )
                )
                continue

            rights_with_procedure = 0
            complete_rights = 0
            incomplete_rights: list[Node] = []

            for right in rights:
                procedures = self._objects(graph, right, PIPA.hasExerciseProcedure)
                evidence += self._assertion_evidence(graph, right, PIPA.hasExerciseProcedure)
                if procedures:
                    rights_with_procedure += 1

                described = False
                for procedure in procedures:
                    evidence += self._assertion_evidence(graph, procedure, PIPA.hasProcedureDescription)
                    if self._nonempty_values(graph, procedure, PIPA.hasProcedureDescription):
                        described = True

                if described:
                    complete_rights += 1
                else:
                    incomplete_rights.append(right)

            if complete_rights == len(rights):
                results.append(
                    InstanceRuleResult(
                        instance_id=str(subject),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(subject, PIPA.hasRight),
                            *[self._fact_key(right, PIPA.hasExerciseProcedure) for right in rights],
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="권리 종류와 행사 방법·절차가 확인됩니다.",
                        recommendation="현재 권리행사 안내를 유지하세요.",
                    )
                )
            elif rights_with_procedure == 0:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(subject),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(subject, PIPA.hasRight)],
                        missing_facts=[self._fact_key(right, PIPA.hasExerciseProcedure) for right in rights],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(right, "hasExerciseProcedure", "권리는 있으나 행사 방법·절차가 없음")
                            for right in rights
                        ],
                        reason="권리는 확인되지만 행사 방법·절차가 확인되지 않습니다.",
                        recommendation="각 권리에 행사 방법·절차를 연결하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(subject),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(subject, PIPA.hasRight)],
                        uncertain_facts=[self._fact_key(right, PIPA.hasExerciseProcedure) for right in incomplete_rights],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(
                                right,
                                "hasExerciseProcedure/hasProcedureDescription",
                                "일부 권리의 절차가 누락되거나 모호함",
                            )
                            for right in incomplete_rights
                        ],
                        reason="일부 권리의 행사 방법·절차만 확인되거나 내용이 모호합니다.",
                        recommendation="모든 권리에 구체적인 행사 방법·절차를 연결하세요.",
                    )
                )
        return results

    # ------------------------------------------------------------------
    # PoC2
    # ------------------------------------------------------------------

    def _p2_r01(self, graph: Graph) -> list[InstanceRuleResult]:
        incidents = self._instances(graph, PIPA.DataBreachIncident)
        if not incidents:
            return self._conditional_no_targets(graph, META.dataBreachIncidentState, "DataBreachIncident")

        results = []
        for incident in incidents:
            raw_affected = self._objects(graph, incident, PIPA.affectsPersonalInformation)
            affected_names, affected_complete = self._item_name_set(graph, raw_affected)
            raw_notices = self._objects(graph, incident, PIPA.hasNotificationNotice)
            notices = self._nonempty_values(graph, incident, PIPA.hasNotificationNotice)

            evidence = self._assertion_evidence(graph, incident, PIPA.affectsPersonalInformation)
            evidence += self._assertion_evidence(graph, incident, PIPA.hasNotificationNotice)
            for item in raw_affected:
                evidence += self._assertion_evidence(graph, item, PIPA.hasItemName)

            if not raw_affected or not affected_complete or not affected_names:
                notes = []
                if not raw_affected:
                    notes.append(
                        self._absence_evidence(
                            incident,
                            "affectsPersonalInformation",
                            "실제 영향 개인정보 Fact를 확인하지 못함",
                        )
                    )
                results.append(
                    InstanceRuleResult(
                        instance_id=str(incident),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        uncertain_facts=[self._fact_key(incident, PIPA.affectsPersonalInformation)],
                        evidence=self._dedupe_evidence(evidence) + notes,
                        reason="DataBreachIncident는 확인되지만 F2-02 실제 영향 개인정보 항목명이 UNKNOWN/모호합니다.",
                        recommendation="F2-02 affectsPersonalInformation을 사고 사실에 맞게 구조화하세요.",
                    )
                )
                continue

            matched = [self._fact_key(incident, PIPA.affectsPersonalInformation)]
            if notices:
                matched.append(self._fact_key(incident, PIPA.hasNotificationNotice))
                results.append(
                    InstanceRuleResult(
                        instance_id=str(incident),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=matched,
                        evidence=self._dedupe_evidence(evidence),
                        reason=(
                            "DataBreachIncident, 실제 영향 개인정보, NotificationNotice 존재가 확인됩니다. "
                            "P2-R01은 통지 대상 여부나 신고 threshold를 자동판정하지 않습니다."
                        ),
                        recommendation="사고 사실과 통지문 존재 근거를 유지하세요.",
                    )
                )
            elif raw_notices:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(incident),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=matched,
                        uncertain_facts=[self._fact_key(incident, PIPA.hasNotificationNotice)],
                        evidence=self._dedupe_evidence(evidence),
                        reason="사고 사실은 확인되지만 NotificationNotice 값이 UNKNOWN/모호합니다.",
                        recommendation="F2-03 hasNotificationNotice의 존재 여부를 명확히 구조화하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(incident),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=matched,
                        missing_facts=[self._fact_key(incident, PIPA.hasNotificationNotice)],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(
                                incident,
                                "hasNotificationNotice",
                                "사고 사실은 확인되지만 NotificationNotice가 없음",
                            )
                        ],
                        reason=(
                            "DataBreachIncident와 실제 영향 개인정보는 확인되지만 NotificationNotice가 없습니다. "
                            "이 결과는 통지 의무 대상 여부 판정이 아닙니다."
                        ),
                        recommendation="제공된 사고 기록에 대응하는 NotificationNotice 존재 여부를 확인하세요.",
                    )
                )
        return results

    def _item_name_set(self, graph: Graph, items: Iterable[Node]) -> tuple[set[str], bool]:
        names: set[str] = set()
        complete = True
        for item in items:
            values = self._nonempty_values(graph, item, PIPA.hasItemName)
            if not values:
                complete = False
            names.update(str(value).strip() for value in values)
        return names, complete

    def _p2_r02(self, graph: Graph) -> list[InstanceRuleResult]:
        incidents = self._instances(graph, PIPA.DataBreachIncident)
        results: list[InstanceRuleResult] = []
        for incident in incidents:
            notices = self._objects(graph, incident, PIPA.hasNotificationNotice)
            if not notices:
                notice_state = self._explicit_state(graph, META.notificationNoticeState)
                if notice_state == "confirmed_false":
                    results.append(
                        InstanceRuleResult(
                            instance_id=str(incident),
                            status=RuleStatus.NOT_APPLICABLE,
                            applicability=Applicability.FALSE,
                            matched_facts=["metadata:notificationNoticeState=confirmed_false"],
                            reason="NotificationNotice가 없다고 명시적으로 확인되었습니다.",
                            recommendation="P2-R01 결과와 함께 해당 없음 상태를 유지하세요.",
                        )
                    )
                else:
                    results.append(
                        InstanceRuleResult(
                            instance_id=str(incident),
                            status=RuleStatus.AMBER,
                            applicability=Applicability.UNKNOWN,
                            uncertain_facts=["NotificationNotice"],
                            evidence=[self._absence_evidence(incident, "hasNotificationNotice", "NotificationNotice의 존재/부재가 명시적으로 확정되지 않음")],
                            reason="NotificationNotice가 추출되지 않았지만 명시적 부재도 확인되지 않아 적용 여부를 확정할 수 없습니다.",
                            recommendation="NotificationNotice 존재 여부를 Fact로 명시하고 P2-R01 결과를 함께 확인하세요.",
                        )
                    )
                continue
            actual_items = self._objects(graph, incident, PIPA.affectsPersonalInformation)
            actual_names, actual_complete = self._item_name_set(graph, actual_items)
            for notice in notices:
                notice_items = self._objects(graph, notice, PIPA.mentionsPersonalInformation)
                notice_names, notice_complete = self._item_name_set(graph, notice_items)
                evidence = self._assertion_evidence(graph, incident, PIPA.affectsPersonalInformation)
                evidence += self._assertion_evidence(graph, notice, PIPA.mentionsPersonalInformation)
                for item in actual_items:
                    evidence += self._assertion_evidence(graph, item, PIPA.hasItemName)
                for item in notice_items:
                    evidence += self._assertion_evidence(graph, item, PIPA.hasItemName)
                if not actual_items or not actual_complete or not notice_complete:
                    results.append(
                        InstanceRuleResult(
                            instance_id=f"{incident}|{notice}",
                            status=RuleStatus.AMBER,
                            applicability=Applicability.TRUE,
                            uncertain_facts=["PersonalInformation.hasItemName"],
                            evidence=self._dedupe_evidence(evidence) or [self._absence_evidence(notice, "mentionsPersonalInformation/hasItemName", "항목 집합 비교에 필요한 값 부족")],
                            reason="실제 영향 항목과 통지문 항목을 정확히 비교할 수 없습니다.",
                            recommendation="실제 영향 항목과 통지문 기재 항목을 구체적인 항목명으로 구조화하세요.",
                        )
                    )
                elif actual_names <= notice_names:
                    results.append(
                        InstanceRuleResult(
                            instance_id=f"{incident}|{notice}",
                            status=RuleStatus.GREEN,
                            applicability=Applicability.TRUE,
                            matched_facts=[
                                self._fact_key(incident, PIPA.affectsPersonalInformation),
                                self._fact_key(notice, PIPA.mentionsPersonalInformation),
                            ],
                            evidence=self._dedupe_evidence(evidence),
                            reason="실제 영향 개인정보 항목이 통지문에 모두 포함됩니다.",
                            recommendation="현재 통지 항목을 유지하세요.",
                        )
                    )
                else:
                    missing_names = sorted(actual_names - notice_names)
                    results.append(
                        InstanceRuleResult(
                            instance_id=f"{incident}|{notice}",
                            status=RuleStatus.RED,
                            applicability=Applicability.TRUE,
                            matched_facts=[self._fact_key(incident, PIPA.affectsPersonalInformation)],
                            missing_facts=[f"notice_item:{name}" for name in missing_names],
                            evidence=self._dedupe_evidence(evidence) + [
                                self._absence_evidence(notice, "mentionsPersonalInformation", f"통지문 누락 항목: {name}") for name in missing_names
                            ],
                            reason="실제 영향 개인정보 중 통지문에 누락된 항목이 있습니다.",
                            recommendation="누락된 개인정보 항목을 통지문에 반영하세요.",
                        )
                    )
        return results or self._conditional_no_targets(graph, META.dataBreachIncidentState, "DataBreachIncident")

    def _p2_r03(self, graph: Graph) -> list[InstanceRuleResult]:
        notices = self._instances(graph, PIPA.NotificationNotice)
        if not notices:
            if self._explicit_state(graph, META.dataBreachIncidentState) == "confirmed_false":
                return self._conditional_no_targets(graph, META.dataBreachIncidentState, "DataBreachIncident")
            return self._conditional_no_targets(graph, META.notificationNoticeState, "NotificationNotice")

        results = []
        for notice in notices:
            raw_notice_time = self._objects(graph, notice, PIPA.noticeIncidentTime)
            raw_circumstances = self._objects(graph, notice, PIPA.hasIncidentCircumstances)
            notice_time = self._nonempty_values(graph, notice, PIPA.noticeIncidentTime)
            circumstances = self._nonempty_values(graph, notice, PIPA.hasIncidentCircumstances)
            evidence = self._assertion_evidence(graph, notice, PIPA.noticeIncidentTime)
            evidence += self._assertion_evidence(graph, notice, PIPA.hasIncidentCircumstances)

            if notice_time and circumstances:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(notice),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(notice, PIPA.noticeIncidentTime),
                            self._fact_key(notice, PIPA.hasIncidentCircumstances),
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="통지문 자체에 유출등 시점과 경위가 모두 기재되어 있습니다.",
                        recommendation="실제 incidentDate와 통지문 기재시점의 분리를 유지하세요.",
                    )
                )
                continue

            missing_predicates: list[URIRef] = []
            if not raw_notice_time:
                missing_predicates.append(PIPA.noticeIncidentTime)
            if not raw_circumstances:
                missing_predicates.append(PIPA.hasIncidentCircumstances)

            if missing_predicates:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(notice),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(notice, predicate)
                            for predicate in (PIPA.noticeIncidentTime, PIPA.hasIncidentCircumstances)
                            if predicate not in missing_predicates
                        ],
                        missing_facts=[self._fact_key(notice, predicate) for predicate in missing_predicates],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(
                                notice,
                                _local_name(predicate),
                                "통지문 필수 기재사항이 명시적으로 부재",
                            )
                            for predicate in missing_predicates
                        ],
                        reason="통지문에서 유출등 시점 또는 경위 중 하나 이상을 확인하지 못했습니다.",
                        recommendation="통지문에 유출등 시점과 경위를 모두 기재하세요.",
                    )
                )
            else:
                uncertain_predicates: list[URIRef] = []
                if not notice_time:
                    uncertain_predicates.append(PIPA.noticeIncidentTime)
                if not circumstances:
                    uncertain_predicates.append(PIPA.hasIncidentCircumstances)

                results.append(
                    InstanceRuleResult(
                        instance_id=str(notice),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        uncertain_facts=[self._fact_key(notice, predicate) for predicate in uncertain_predicates],
                        evidence=self._dedupe_evidence(evidence),
                        reason="통지문 시점 또는 경위 값이 UNKNOWN/모호하여 자동 확정할 수 없습니다.",
                        recommendation="통지문에 유출등 시점과 경위를 구체적으로 명시하세요.",
                    )
                )
        return results

    def _p2_r08(self, graph: Graph) -> list[InstanceRuleResult]:
        incidents = self._instances(graph, PIPA.DataBreachIncident)
        if not incidents:
            return self._conditional_no_targets(graph, META.dataBreachIncidentState, "DataBreachIncident")

        required_roles = {
            "data_subject_guidance",
            "controller_response",
            "remedy_procedure",
            "post_incident_mitigation",
        }
        results = []
        for incident in incidents:
            measures = self._objects(graph, incident, PIPA.hasResponseMeasure)
            role_map: dict[str, list[Node]] = {}
            evidence = self._assertion_evidence(graph, incident, PIPA.hasResponseMeasure)

            for measure in measures:
                evidence += self._source_evidence(graph, measure)
                for role_value in self._nonempty_values(graph, measure, PIPA.measureRole):
                    role = str(role_value).strip()
                    role_map.setdefault(role, []).append(measure)
                    evidence += self._assertion_evidence(graph, measure, PIPA.measureRole)

            found_roles = set(role_map)
            confirmed_required_roles = required_roles & found_roles
            missing_roles = sorted(required_roles - found_roles)
            unexpected_roles = sorted(found_roles - required_roles)

            if found_roles == required_roles:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(incident),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[f"measure_role:{role}" for role in sorted(required_roles)],
                        evidence=self._dedupe_evidence(evidence),
                        reason="v1에서 허용된 필수 4개 역할의 대응·구제 정보가 모두 확인됩니다.",
                        recommendation="역할별 대응정보와 원문 근거를 유지하세요.",
                    )
                )
            elif measures:
                uncertain_facts = [f"measure_role:{role}" for role in missing_roles]
                uncertain_facts += [f"unexpected_measure_role:{role}" for role in unexpected_roles]
                notes = [
                    self._absence_evidence(incident, "measureRole", f"미확인 역할: {role}")
                    for role in missing_roles
                ]
                notes += [
                    self._absence_evidence(incident, "measureRole", f"v1 비허용 역할: {role}")
                    for role in unexpected_roles
                ]
                results.append(
                    InstanceRuleResult(
                        instance_id=str(incident),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[f"measure_role:{role}" for role in sorted(confirmed_required_roles)],
                        uncertain_facts=uncertain_facts,
                        evidence=self._dedupe_evidence(evidence) + notes,
                        reason=(
                            "대응정보는 존재하지만 v1 필수 4개 역할 중 일부가 누락되었거나 "
                            "허용되지 않은 역할 값이 포함되어 있습니다."
                        ),
                        recommendation=(
                            "measure_role을 data_subject_guidance, controller_response, remedy_procedure, "
                            "post_incident_mitigation 4종으로만 구분해 명시하세요."
                        ),
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(incident),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        missing_facts=[f"measure_role:{role}" for role in sorted(required_roles)],
                        evidence=[self._absence_evidence(incident, "hasResponseMeasure", "필수 대응정보를 확인하지 못함")],
                        reason="필수 대응·구제 정보가 확인되지 않습니다.",
                        recommendation="제34조제1항제3·4호 및 제3항에 대응하는 정보를 역할별로 명시하세요.",
                    )
                )
        return results

    # ------------------------------------------------------------------
    # PoC3
    # ------------------------------------------------------------------

    def _collection_activities(self, graph: Graph) -> list[Node]:
        return self._instances(graph, PIPA.CollectionAndUse)

    def _is_consent_basis(self, graph: Graph, basis: Node) -> bool:
        return self._is_instance_of(graph, basis, PIPA.Consent)

    def _consent_applicability(self, graph: Graph, activity: Node) -> tuple[Applicability, list[Node]]:
        bases = self._objects(graph, activity, PIPA.hasLegalBasis)
        if not bases:
            return Applicability.UNKNOWN, []

        consent_bases = [basis for basis in bases if self._is_consent_basis(graph, basis)]
        if consent_bases:
            return Applicability.TRUE, consent_bases

        if all(self._has_specific_legal_basis_type(graph, basis) for basis in bases):
            return Applicability.FALSE, bases

        return Applicability.UNKNOWN, bases

    def _p3_r01(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._collection_activities(graph)
        if not activities:
            return self._conditional_no_targets(graph, META.collectionAndUseState, "CollectionAndUse")

        results = []
        for activity in activities:
            bases = self._objects(graph, activity, PIPA.hasLegalBasis)
            if not bases:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        missing_facts=[self._fact_key(activity, PIPA.hasLegalBasis)],
                        evidence=[self._absence_evidence(activity, "hasLegalBasis", "법적근거 미지정")],
                        reason="수집·이용 처리행위의 법적근거가 지정되지 않았습니다.",
                        recommendation="해당 처리행위에 법적근거를 명시하세요.",
                    )
                )
                continue

            evidence = self._assertion_evidence(graph, activity, PIPA.hasLegalBasis)
            unknown_bases = [basis for basis in bases if not self._has_specific_legal_basis_type(graph, basis)]
            if unknown_bases:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(activity, PIPA.hasLegalBasis)],
                        uncertain_facts=[f"legal_basis_type:{_local_name(basis)}" for basis in unknown_bases],
                        evidence=self._dedupe_evidence(evidence),
                        reason="법적근거 연결은 있으나 근거 유형이 UNKNOWN/모호합니다.",
                        recommendation="법적근거의 구체적인 유형을 명시하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(activity, PIPA.hasLegalBasis)],
                        evidence=self._dedupe_evidence(evidence),
                        reason="수집·이용 처리행위의 법적근거 유형이 명시되어 있습니다.",
                        recommendation="법적근거와 원문 근거를 유지하세요.",
                    )
                )
        return results

    def _consent_rule(
        self,
        graph: Graph,
        *,
        required_predicates: tuple[URIRef, ...],
        title: str,
        recommendation: str,
        detail_requirements: tuple[tuple[URIRef, URIRef], ...] = (),
    ) -> list[InstanceRuleResult]:
        activities = self._collection_activities(graph)
        if not activities:
            return self._conditional_no_targets(graph, META.collectionAndUseState, "CollectionAndUse")

        results = []
        for activity in activities:
            applicability, _ = self._consent_applicability(graph, activity)

            if applicability == Applicability.FALSE:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.NOT_APPLICABLE,
                        applicability=Applicability.FALSE,
                        matched_facts=[self._fact_key(activity, PIPA.hasLegalBasis)],
                        evidence=self._assertion_evidence(graph, activity, PIPA.hasLegalBasis),
                        reason="동의 기반 처리행위가 아니므로 적용 대상이 아닙니다.",
                        recommendation="해당 없음으로 유지합니다.",
                    )
                )
                continue

            if applicability == Applicability.UNKNOWN:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.UNKNOWN,
                        uncertain_facts=[self._fact_key(activity, PIPA.hasLegalBasis)],
                        evidence=self._assertion_evidence(graph, activity, PIPA.hasLegalBasis) or [
                            self._absence_evidence(activity, "hasLegalBasis", "동의 기반 여부를 확인할 수 없음")
                        ],
                        reason="동의 기반 처리 여부가 불명확합니다.",
                        recommendation="법적근거 유형을 먼저 명시하세요.",
                    )
                )
                continue

            missing = [predicate for predicate in required_predicates if not self._objects(graph, activity, predicate)]
            evidence = self._assertion_evidence(graph, activity, PIPA.hasLegalBasis)
            for predicate in required_predicates:
                evidence += self._assertion_evidence(graph, activity, predicate)

            if missing:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(activity, predicate)
                            for predicate in required_predicates
                            if predicate not in missing
                        ],
                        missing_facts=[self._fact_key(activity, predicate) for predicate in missing],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(
                                activity,
                                _local_name(predicate),
                                f"동의 기반 {title} 요건 누락",
                            )
                            for predicate in missing
                        ],
                        reason=f"동의 기반 처리의 {title} 요건이 누락되었습니다.",
                        recommendation=recommendation,
                    )
                )
                continue

            ambiguous: list[tuple[Node, URIRef]] = []
            for relation, detail_predicate in detail_requirements:
                for linked in self._objects(graph, activity, relation):
                    evidence += self._assertion_evidence(graph, linked, detail_predicate)
                    if not self._nonempty_values(graph, linked, detail_predicate):
                        ambiguous.append((linked, detail_predicate))

            if ambiguous:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(activity, predicate) for predicate in required_predicates],
                        uncertain_facts=[self._fact_key(linked, predicate) for linked, predicate in ambiguous],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(
                                linked,
                                _local_name(predicate),
                                f"동의 기반 {title} 값이 포괄적이거나 모호함",
                            )
                            for linked, predicate in ambiguous
                        ],
                        reason=f"동의 기반 처리의 {title} 연결은 있으나 구체 값이 모호합니다.",
                        recommendation=recommendation,
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(activity, PIPA.hasLegalBasis),
                            *[self._fact_key(activity, predicate) for predicate in required_predicates],
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason=f"동의 기반 처리의 {title} 요건이 구조화되어 있습니다.",
                        recommendation="현재 동의 설계 연결을 유지하세요.",
                    )
                )
        return results

    def _p3_r02(self, graph: Graph) -> list[InstanceRuleResult]:
        return self._consent_rule(
            graph,
            required_predicates=(PIPA.hasConsentRequest, PIPA.hasPurpose),
            detail_requirements=((PIPA.hasPurpose, PIPA.hasPurposeDescription),),
            title="처리목적 고지 설계",
            recommendation="ConsentRequest와 구체적 처리목적을 해당 CollectionAndUse에 연결하세요.",
        )

    def _p3_r03(self, graph: Graph) -> list[InstanceRuleResult]:
        return self._consent_rule(
            graph,
            required_predicates=(PIPA.hasConsentRequest, PIPA.hasPersonalInformation),
            detail_requirements=((PIPA.hasPersonalInformation, PIPA.hasItemName),),
            title="개인정보 항목 고지 설계",
            recommendation="ConsentRequest와 구체적 개인정보 항목을 해당 CollectionAndUse에 연결하세요.",
        )

    def _p3_r04(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._collection_activities(graph)
        if not activities:
            return self._conditional_no_targets(graph, META.collectionAndUseState, "CollectionAndUse")

        results = []
        for activity in activities:
            applicability, _ = self._consent_applicability(graph, activity)

            if applicability == Applicability.FALSE:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.NOT_APPLICABLE,
                        applicability=Applicability.FALSE,
                        matched_facts=[self._fact_key(activity, PIPA.hasLegalBasis)],
                        evidence=self._assertion_evidence(graph, activity, PIPA.hasLegalBasis),
                        reason="동의 기반 처리행위가 아니므로 적용 대상이 아닙니다.",
                        recommendation="해당 없음으로 유지합니다.",
                    )
                )
                continue

            if applicability == Applicability.UNKNOWN:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.UNKNOWN,
                        uncertain_facts=[self._fact_key(activity, PIPA.hasLegalBasis)],
                        evidence=self._assertion_evidence(graph, activity, PIPA.hasLegalBasis) or [
                            self._absence_evidence(activity, "hasLegalBasis", "동의 기반 여부 불명")
                        ],
                        reason="동의 기반 처리 여부가 불명확합니다.",
                        recommendation="법적근거 유형을 먼저 명시하세요.",
                    )
                )
                continue

            requests = self._objects(graph, activity, PIPA.hasConsentRequest)
            retentions = self._objects(graph, activity, PIPA.hasRetention)
            complete, evidence, matched = self._retention_complete(graph, activity)
            combined_evidence = self._dedupe_evidence(
                self._assertion_evidence(graph, activity, PIPA.hasLegalBasis)
                + self._assertion_evidence(graph, activity, PIPA.hasConsentRequest)
                + evidence
            )

            if not requests:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(activity, PIPA.hasLegalBasis), *matched],
                        missing_facts=[self._fact_key(activity, PIPA.hasConsentRequest)],
                        evidence=combined_evidence + [
                            self._absence_evidence(
                                activity,
                                "hasConsentRequest",
                                "P3-R04 frozen coverage의 F3-03 동의요청 설계가 없음",
                            )
                        ],
                        reason="동의 기반 처리이나 F3-03 ConsentRequest 설계가 확인되지 않습니다.",
                        recommendation="CollectionAndUse에 ConsentRequest를 연결하고 보유·이용기간/종료조건을 함께 명시하세요.",
                    )
                )
                continue

            if complete:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(activity, PIPA.hasLegalBasis),
                            self._fact_key(activity, PIPA.hasConsentRequest),
                            *matched,
                        ],
                        evidence=combined_evidence,
                        reason="동의요청과 보유기간 또는 식별 가능한 종료조건이 함께 설계되어 있습니다.",
                        recommendation="현재 보유기간 설계를 유지하세요.",
                    )
                )
                continue

            has_partial_retention_structure = any(
                self._objects(graph, retention, PIPA.hasRetentionPeriod)
                or self._objects(graph, retention, PIPA.hasRetentionEndCondition)
                for retention in retentions
            )

            if retentions and has_partial_retention_structure:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(activity, PIPA.hasLegalBasis),
                            self._fact_key(activity, PIPA.hasConsentRequest),
                            self._fact_key(activity, PIPA.hasRetention),
                        ],
                        uncertain_facts=["Retention.hasRetentionPeriod/hasRetentionEndCondition"],
                        evidence=combined_evidence,
                        reason="보유정보 연결은 있으나 기간 값 또는 식별 가능한 종료조건이 모호합니다.",
                        recommendation="RetentionPeriod의 기간 값 또는 RetentionEndCondition의 구체적 종료조건을 명시하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(activity, PIPA.hasLegalBasis),
                            self._fact_key(activity, PIPA.hasConsentRequest),
                        ],
                        missing_facts=[self._fact_key(activity, PIPA.hasRetention)],
                        evidence=combined_evidence + [
                            self._absence_evidence(activity, "hasRetention", "동의 기반 보유기간/종료조건 미설계")
                        ],
                        reason="동의 기반 처리의 보유기간 또는 종료조건이 설계되지 않았습니다.",
                        recommendation="Retention과 기간 또는 종료조건을 해당 CollectionAndUse에 연결하세요.",
                    )
                )
        return results

    def _p3_r05(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._collection_activities(graph)
        if not activities:
            return self._conditional_no_targets(graph, META.collectionAndUseState, "CollectionAndUse")
        results = []
        for activity in activities:
            items = self._objects(graph, activity, PIPA.hasPersonalInformation)
            evidence = self._assertion_evidence(graph, activity, PIPA.hasPersonalInformation)
            if not items:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        uncertain_facts=[self._fact_key(activity, PIPA.hasPersonalInformation)],
                        evidence=[self._absence_evidence(activity, "hasPersonalInformation", "수집 항목 설계 확인 불가")],
                        reason="최소수집 설계를 평가할 개인정보 항목이 확인되지 않습니다.",
                        recommendation="수집 개인정보 항목과 필수/선택 구분을 구조화하세요.",
                    )
                )
                continue

            missing_required_flags: list[Node] = []
            uncertain_required_flags: list[Node] = []
            missing_names: list[Node] = []
            uncertain_names: list[Node] = []
            required_without_rationale: list[Node] = []
            required_with_uncertain_rationale: list[Node] = []
            matched = [self._fact_key(activity, PIPA.hasPersonalInformation)]

            for item in items:
                raw_names = self._objects(graph, item, PIPA.hasItemName)
                names = self._nonempty_values(graph, item, PIPA.hasItemName)
                flags = self._objects(graph, item, PIPA.isRequired)
                raw_rationales = self._objects(graph, item, PIPA.designRationale)
                rationales = self._nonempty_values(graph, item, PIPA.designRationale)
                evidence += self._assertion_evidence(graph, item, PIPA.hasItemName)
                evidence += self._assertion_evidence(graph, item, PIPA.isRequired)
                evidence += self._assertion_evidence(graph, item, PIPA.designRationale)

                if not raw_names:
                    missing_names.append(item)
                elif not names:
                    uncertain_names.append(item)
                else:
                    matched.append(self._fact_key(item, PIPA.hasItemName))

                if not flags:
                    missing_required_flags.append(item)
                    continue

                parsed_flags = [_as_bool(flag) for flag in flags]
                known_flags = {value for value in parsed_flags if value is not None}
                flag_is_uncertain = any(value is None for value in parsed_flags) or len(known_flags) > 1
                if flag_is_uncertain or not known_flags:
                    uncertain_required_flags.append(item)
                else:
                    matched.append(self._fact_key(item, PIPA.isRequired))

                if True in known_flags:
                    if not raw_rationales:
                        required_without_rationale.append(item)
                    elif not rationales:
                        required_with_uncertain_rationale.append(item)
                    else:
                        matched.append(self._fact_key(item, PIPA.designRationale))

            if required_without_rationale:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=matched,
                        missing_facts=[self._fact_key(item, PIPA.designRationale) for item in required_without_rationale],
                        uncertain_facts=[
                            *[self._fact_key(item, PIPA.isRequired) for item in missing_required_flags + uncertain_required_flags],
                            *[self._fact_key(item, PIPA.hasItemName) for item in missing_names + uncertain_names],
                            *[self._fact_key(item, PIPA.designRationale) for item in required_with_uncertain_rationale],
                        ],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(item, "designRationale", "필수 지정 항목의 설계사유 부재")
                            for item in required_without_rationale
                        ],
                        reason="필수 지정 개인정보 항목에 최소수집 설계 사유가 누락되었습니다.",
                        recommendation="isRequired=true인 각 항목에 designRationale을 명시하세요.",
                    )
                )
            elif (
                missing_required_flags
                or uncertain_required_flags
                or missing_names
                or uncertain_names
                or required_with_uncertain_rationale
            ):
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=matched,
                        uncertain_facts=[
                            *[self._fact_key(item, PIPA.isRequired) for item in missing_required_flags + uncertain_required_flags],
                            *[self._fact_key(item, PIPA.hasItemName) for item in missing_names + uncertain_names],
                            *[self._fact_key(item, PIPA.designRationale) for item in required_with_uncertain_rationale],
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="일부 항목의 이름, 필수/선택 값 또는 최소수집 설계 사유가 UNKNOWN/모호합니다.",
                        recommendation="각 수집 항목의 이름, isRequired 값, 필수항목의 designRationale을 구체적으로 명시하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=matched,
                        evidence=self._dedupe_evidence(evidence),
                        reason="필수 지정 개인정보 항목마다 최소수집 설계 사유가 확인됩니다.",
                        recommendation="항목별 설계 사유를 유지하세요.",
                    )
                )
        return results

    def _p3_r06(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._collection_activities(graph)
        if not activities:
            return self._conditional_no_targets(graph, META.collectionAndUseState, "CollectionAndUse")

        optional_items: list[tuple[Node, Node]] = []
        unknown_items: list[tuple[Node, Node]] = []

        for activity in activities:
            for item in self._objects(graph, activity, PIPA.hasPersonalInformation):
                flags = self._objects(graph, item, PIPA.isRequired)
                parsed_flags = [_as_bool(flag) for flag in flags]
                if not flags or all(value is None for value in parsed_flags):
                    unknown_items.append((activity, item))
                elif any(value is False for value in parsed_flags):
                    optional_items.append((activity, item))

        if not optional_items:
            if unknown_items:
                return [
                    InstanceRuleResult(
                        instance_id="__document__",
                        status=RuleStatus.AMBER,
                        applicability=Applicability.UNKNOWN,
                        uncertain_facts=[self._fact_key(item, PIPA.isRequired) for _, item in unknown_items],
                        evidence=[
                            self._absence_evidence(item, "isRequired", "선택항목 존재 여부 확인 불가")
                            for _, item in unknown_items
                        ],
                        reason="필수·선택 구분이 불완전하여 규칙 적용 여부를 확정할 수 없습니다.",
                        recommendation="각 개인정보 항목의 isRequired 값을 명시하세요.",
                    )
                ]

            return [
                InstanceRuleResult(
                    instance_id="__document__",
                    status=RuleStatus.NOT_APPLICABLE,
                    applicability=Applicability.FALSE,
                    matched_facts=["no_optional_items"],
                    reason="선택항목이 없으므로 적용 대상이 아닙니다.",
                    recommendation="해당 없음으로 유지합니다.",
                )
            ]

        results = []
        for activity, item in optional_items:
            requests = self._objects(graph, activity, PIPA.hasConsentRequest)
            evidence = self._assertion_evidence(graph, item, PIPA.isRequired)
            evidence += self._assertion_evidence(graph, activity, PIPA.hasConsentRequest)

            if not requests:
                results.append(
                    InstanceRuleResult(
                        instance_id=f"{activity}|{item}",
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(item, PIPA.isRequired)],
                        uncertain_facts=[self._fact_key(activity, PIPA.hasConsentRequest)],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(activity, "hasConsentRequest", "선택항목의 동의요청 설계 연결 불명")
                        ],
                        reason="선택항목은 확인되지만 동의요청 설계 연결이 불명확합니다.",
                        recommendation="선택항목이 속한 CollectionAndUse에 ConsentRequest를 연결하세요.",
                    )
                )
                continue

            values = [
                value
                for request in requests
                for value in self._objects(graph, request, PIPA.deniesServiceOnOptionalRefusal)
            ]
            for request in requests:
                evidence += self._assertion_evidence(graph, request, PIPA.deniesServiceOnOptionalRefusal)

            bool_values = [_as_bool(value) for value in values]

            if any(value is True for value in bool_values):
                results.append(
                    InstanceRuleResult(
                        instance_id=f"{activity}|{item}",
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(item, PIPA.isRequired),
                            *[self._fact_key(request, PIPA.deniesServiceOnOptionalRefusal) for request in requests],
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="선택정보 미동의를 이유로 서비스 제공을 거부하도록 설계되어 있습니다.",
                        recommendation="선택정보 미동의 시 서비스 거부가 발생하지 않도록 설계를 수정하세요.",
                    )
                )
            elif values and all(value is False for value in bool_values):
                results.append(
                    InstanceRuleResult(
                        instance_id=f"{activity}|{item}",
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(item, PIPA.isRequired),
                            *[self._fact_key(request, PIPA.deniesServiceOnOptionalRefusal) for request in requests],
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="선택정보 미동의 시 서비스 제공 거부가 false로 명시되어 있습니다.",
                        recommendation="현재 선택동의 설계를 유지하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=f"{activity}|{item}",
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(item, PIPA.isRequired)],
                        uncertain_facts=[
                            *[
                                self._fact_key(request, PIPA.deniesServiceOnOptionalRefusal)
                                for request in requests
                            ]
                        ],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(
                                activity,
                                "deniesServiceOnOptionalRefusal",
                                "값이 없거나 UNKNOWN",
                            )
                        ],
                        reason="선택정보 미동의 시 서비스 거부 여부가 불명확합니다.",
                        recommendation="deniesServiceOnOptionalRefusal을 true/false로 명시하세요.",
                    )
                )
        return results

    def _p3_r08(self, graph: Graph) -> list[InstanceRuleResult]:
        retentions = self._instances(graph, PIPA.Retention)
        end_conditions = self._instances(graph, PIPA.RetentionEndCondition)
        if not retentions and not end_conditions:
            return self._conditional_no_targets(graph, META.retentionState, "Retention/RetentionEndCondition")
        target_ends: set[Node] = set(end_conditions)
        for retention in retentions:
            target_ends.update(self._objects(graph, retention, PIPA.hasRetentionEndCondition))
        if not target_ends:
            return [
                InstanceRuleResult(
                    instance_id="__document__",
                    status=RuleStatus.RED,
                    applicability=Applicability.TRUE,
                    missing_facts=["Retention.hasRetentionEndCondition"],
                    evidence=[self._absence_evidence("__document__", "hasRetentionEndCondition", "보유 종료조건은 있으나 구조화되지 않음")],
                    reason="보유 종료조건을 확인하지 못했습니다.",
                    recommendation="Retention에 RetentionEndCondition을 연결하세요.",
                )
            ]
        results = []
        for end in sorted(target_ends, key=str):
            destructions = self._objects(graph, end, PIPA.triggersDestruction)
            evidence = self._assertion_evidence(graph, end, PIPA.triggersDestruction)
            if not destructions:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(end),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        missing_facts=[self._fact_key(end, PIPA.triggersDestruction)],
                        evidence=[self._absence_evidence(end, "triggersDestruction", "종료조건에서 파기 연결 부재")],
                        reason="보유 종료조건은 있으나 파기 설계가 연결되지 않았습니다.",
                        recommendation="RetentionEndCondition에서 Destruction으로 triggersDestruction을 연결하세요.",
                    )
                )
                continue
            methods = [
                method
                for destruction in destructions
                for method in self._nonempty_values(graph, destruction, PIPA.hasDestructionMethod)
            ]
            for destruction in destructions:
                evidence += self._assertion_evidence(graph, destruction, PIPA.hasDestructionMethod)
            if methods:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(end),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=[
                            self._fact_key(end, PIPA.triggersDestruction),
                            *[self._fact_key(destruction, PIPA.hasDestructionMethod) for destruction in destructions],
                        ],
                        evidence=self._dedupe_evidence(evidence),
                        reason="보유 종료조건에서 파기 활동과 구체적 방법까지 연결되어 있습니다.",
                        recommendation="현재 종료조건-파기 설계 연결을 유지하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(end),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=[self._fact_key(end, PIPA.triggersDestruction)],
                        uncertain_facts=[self._fact_key(destruction, PIPA.hasDestructionMethod) for destruction in destructions],
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(destruction, "hasDestructionMethod", "파기 방법 미지정") for destruction in destructions
                        ],
                        reason="파기 설계는 연결되었으나 방법이 명확하지 않습니다.",
                        recommendation="연결된 Destruction에 hasDestructionMethod를 명시하세요.",
                    )
                )
        return results

    def _p3_r11(self, graph: Graph) -> list[InstanceRuleResult]:
        activities = self._instances(graph, PIPA.EntrustedProcessing)
        if not activities:
            return self._conditional_no_targets(graph, META.entrustedProcessingState, "EntrustedProcessing")

        results = []
        for activity in activities:
            processors = self._objects(graph, activity, PIPA.hasProcessor)
            raw_task = self._objects(graph, activity, PIPA.entrustedTaskText)
            task = self._nonempty_values(graph, activity, PIPA.entrustedTaskText)
            evidence = self._assertion_evidence(graph, activity, PIPA.hasProcessor)
            evidence += self._assertion_evidence(graph, activity, PIPA.entrustedTaskText)

            missing_facts: list[str] = []
            uncertain_facts: list[str] = []
            matched_facts: list[str] = []

            processors_missing_name: list[Node] = []
            processors_uncertain_name: list[Node] = []
            processors_with_name: list[Node] = []
            for processor in processors:
                raw_names = self._objects(graph, processor, PIPA.hasName)
                names = self._nonempty_values(graph, processor, PIPA.hasName)
                evidence += self._assertion_evidence(graph, processor, PIPA.hasName)
                if names:
                    processors_with_name.append(processor)
                elif raw_names:
                    processors_uncertain_name.append(processor)
                else:
                    processors_missing_name.append(processor)

            if processors:
                matched_facts.append(self._fact_key(activity, PIPA.hasProcessor))
            else:
                missing_facts.append(self._fact_key(activity, PIPA.hasProcessor))

            missing_facts.extend(
                self._fact_key(processor, PIPA.hasName)
                for processor in processors_missing_name
            )
            uncertain_facts.extend(
                self._fact_key(processor, PIPA.hasName)
                for processor in processors_uncertain_name
            )
            matched_facts.extend(
                self._fact_key(processor, PIPA.hasName)
                for processor in processors_with_name
            )

            if task:
                matched_facts.append(self._fact_key(activity, PIPA.entrustedTaskText))
            elif raw_task:
                uncertain_facts.append(self._fact_key(activity, PIPA.entrustedTaskText))
            else:
                missing_facts.append(self._fact_key(activity, PIPA.entrustedTaskText))

            if missing_facts:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.RED,
                        applicability=Applicability.TRUE,
                        matched_facts=matched_facts,
                        missing_facts=missing_facts,
                        uncertain_facts=uncertain_facts,
                        evidence=self._dedupe_evidence(evidence) + [
                            self._absence_evidence(activity, fact.rsplit(":", 1)[-1], "처리위탁 설계 필수정보 누락")
                            for fact in missing_facts
                        ],
                        reason="처리위탁 설계에서 F3-12 수탁자명 또는 F3-13 위탁업무가 누락되었습니다.",
                        recommendation="각 EntrustedProcessor의 hasName과 entrustedTaskText를 모두 명시하세요.",
                    )
                )
            elif uncertain_facts:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.AMBER,
                        applicability=Applicability.TRUE,
                        matched_facts=matched_facts,
                        uncertain_facts=uncertain_facts,
                        evidence=self._dedupe_evidence(evidence),
                        reason="수탁자명 또는 위탁업무 값이 UNKNOWN/모호하여 자동 확정할 수 없습니다.",
                        recommendation="수탁자명과 위탁업무 내용을 구체적으로 명시하세요.",
                    )
                )
            else:
                results.append(
                    InstanceRuleResult(
                        instance_id=str(activity),
                        status=RuleStatus.GREEN,
                        applicability=Applicability.TRUE,
                        matched_facts=matched_facts,
                        evidence=self._dedupe_evidence(evidence),
                        reason="처리위탁 설계의 수탁자명과 위탁업무가 확인됩니다.",
                        recommendation="현재 수탁자-위탁업무 설계를 유지하세요.",
                    )
                )
        return results
