from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

ALLOWED_ORIGIN = "http://localhost:5173"
DISALLOWED_ORIGIN = "http://evil.example.com"


def test_preflight_from_allowed_origin_grants_access_control_allow_origin():
    response = client.options(
        "/api/v1/compliance/policy-check",
        headers={
            "origin": ALLOWED_ORIGIN,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_actual_response_from_allowed_origin_grants_access_control_allow_origin():
    response = client.get("/health", headers={"origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_preflight_from_disallowed_origin_does_not_grant_cors_header():
    response = client.options(
        "/api/v1/compliance/policy-check",
        headers={
            "origin": DISALLOWED_ORIGIN,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_actual_response_from_disallowed_origin_does_not_grant_cors_header():
    response = client.get("/health", headers={"origin": DISALLOWED_ORIGIN})

    assert "access-control-allow-origin" not in response.headers
