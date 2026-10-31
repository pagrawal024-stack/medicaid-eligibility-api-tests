"""Health check and authentication."""
import pytest

from framework import config
from framework.schema_validator import assert_matches_schema


@pytest.mark.smoke
def test_health_check_is_up(anonymous_client):
    response = anonymous_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
    assert response.elapsed.total_seconds() < config.MAX_RESPONSE_TIME_SECONDS


@pytest.mark.smoke
def test_valid_credentials_return_bearer_token(auth_api):
    response = auth_api.get_token(config.CLIENT_ID, config.CLIENT_SECRET)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert len(body["access_token"]) >= 32
    assert body["expires_in"] > 0


@pytest.mark.regression
@pytest.mark.parametrize(
    "client_id, client_secret",
    [
        ("qa-client", "wrong-secret"),
        ("unknown-client", "qa-secret"),
        ("", ""),
    ],
    ids=["wrong_secret", "unknown_client", "empty_credentials"],
)
def test_invalid_credentials_are_rejected(auth_api, client_id, client_secret):
    response = auth_api.get_token(client_id, client_secret)

    assert response.status_code == 401
    assert response.json()["error"] == "INVALID_CLIENT"
    assert "access_token" not in response.json()


@pytest.mark.regression
@pytest.mark.parametrize(
    "auth_header",
    [None, "Bearer not-a-real-token", "Basic cWEtY2xpZW50OnFhLXNlY3JldA=="],
    ids=["no_header", "invalid_token", "wrong_scheme"],
)
def test_protected_endpoint_requires_valid_token(anonymous_client, auth_header):
    headers = {"Authorization": auth_header} if auth_header else {}

    response = anonymous_client.get("/api/v1/applicants/1", headers=headers)

    assert response.status_code == 401
    assert_matches_schema(response.json(), "error")
    assert response.json()["error"] == "UNAUTHORIZED"
