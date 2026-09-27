# PoC2 Frozen Facts

## Scope

PoC2 supports review of personal-information breach notification requirements using:

- incident information;
- existing notification information;
- existing response/remediation information.

PoC2 v1 does not automatically determine ReportingObligation and does not generate a notification notice.

## Frozen Fact IDs

Exactly 10 PoC2 Fact types exist:

- F2-01
- F2-02
- F2-03
- F2-04
- F2-05
- F2-06
- F2-07
- F2-08
- F2-09
- F2-10

Do not invent additional F2 Fact IDs.

When the request explicitly omits the whole notification document, the
service records `NotificationNotice=confirmed_false` as system metadata.
Notice-side property Facts may still be `absent`, but that property state is
not itself the activity-presence signal.

## Fact Contract

Every produced Fact must follow:

docs/context/core/CONTRACTS.md

## Incident and Notice Separation

Incident facts and notification-notice facts are distinct.

Never collapse:

incident.affectsPersonalInformation

into:

notice.mentionsPersonalInformation

and never collapse:

incidentDate

into:

notice_incident_time

These fields may describe related events but have different provenance and semantics.

## Source Types

Incident Facts normally use:

- incident_record

Notification Facts normally use:

- notification_notice

derived may be used only where allowed by the frozen Fact contract.

Do not assign notification_notice provenance to incident evidence or incident_record provenance to notice evidence merely because the values are similar.

## Value State

Use only:

- confirmed
- unknown
- absent

Confirmed false must remain confirmed false.

unknown and absent must remain distinguishable.

## Evidence

Every extracted Fact must retain evidence traceable to the corresponding incident or notification input.

Do not fabricate evidence.

## Mapping

Authoritative Fact-to-ontology mapping:

app/mapping/mapping_registry.py

Do not duplicate or reinterpret it.

## Important v1 Boundary

Do not add:

- triggersNotificationObligation
- automatic ReportingObligation Facts
- notification/reporting threshold Facts
- correction-notice provenance Facts

unless the project scope is explicitly expanded later.
