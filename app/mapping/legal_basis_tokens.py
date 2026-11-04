"""Single source of truth for PoC3 legal basis tokens (F3-02).

No ontology class is added: Consent keeps its ontology class, the other
accepted tokens are plain ``pipa:LegalBasis`` nodes recognised by their
``rdfs:label``.  Matching is exact after trimming and case folding; there is
no substring matching and no alias (e.g. "비동의" is never Consent).
"""

from __future__ import annotations

from typing import Any

CONSENT = "Consent"
NON_CONSENT_TOKENS: tuple[str, ...] = ("Contract", "LegalObligation")
ALLOWED_TOKENS: tuple[str, ...] = (CONSENT, *NON_CONSENT_TOKENS)

# legal_basis.status -> F3-02 value_state.  A missing key means "confirmed".
STATUS_TO_VALUE_STATE = {
    "confirmed": "confirmed",
    "planned": "confirmed",
    "unknown": "unknown",
}

_BY_FOLDED = {token.casefold(): token for token in ALLOWED_TOKENS}
_TYPE_KEYS = ("type", "basis", "name")


def normalize_token(text: Any) -> str | None:
    """Canonical allowed token for ``text`` or None (exact match only)."""
    if not isinstance(text, str):
        return None
    return _BY_FOLDED.get(text.strip().casefold())


def legal_basis_type_text(legal_basis: Any) -> str | None:
    """The raw type text of a legal_basis value (object or plain string)."""
    if isinstance(legal_basis, dict):
        for key in _TYPE_KEYS:
            if legal_basis.get(key) not in (None, ""):
                legal_basis = legal_basis[key]
                break
        else:
            return None
    return legal_basis if isinstance(legal_basis, str) else None


def is_consent_token(text: Any) -> bool:
    return normalize_token(text) == CONSENT


def is_non_consent_token(text: Any) -> bool:
    return normalize_token(text) in NON_CONSENT_TOKENS
