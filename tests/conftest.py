"""Shared fixtures.

By default a fresh copy of the API is started on a free port with its own
temporary SQLite database, so every run is isolated and repeatable. Set
BASE_URL (and DB_PATH) to run the same tests against an API that is already up.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from framework import config
from framework.api_client import ApiClient
from framework.data_factory import applicant_payload, application_payload
from framework.db_validator import DbValidator
from framework.services.applicant_service import ApplicantService
from framework.services.application_service import ApplicationService
from framework.services.auth_service import AuthService

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).parent / "data"


def load_json(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(base_url: str, proc: subprocess.Popen, timeout: float = 20) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"API exited early:\n{proc.stdout.read()}")
        try:
            if requests.get(f"{base_url}/health", timeout=1).status_code == 200:
                return
        except requests.ConnectionError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"API did not start within {timeout}s")


@pytest.fixture(scope="session")
def environment(tmp_path_factory):
    """Yields (base_url, db_path) for the API under test."""
    if config.BASE_URL:
        yield config.BASE_URL.rstrip("/"), config.DB_PATH
        return

    db_path = str(tmp_path_factory.mktemp("db") / "eligibility_test.db")
    port = _free_port()
    env = {**os.environ, "PORT": str(port), "DB_PATH": db_path, "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.main"], cwd=PROJECT_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_up(base_url, proc)
        yield base_url, db_path
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="session")
def base_url(environment):
    return environment[0]


@pytest.fixture(scope="session")
def db(environment):
    db_path = environment[1]
    if not db_path:
        pytest.skip("DB_PATH not set, skipping database validation")
    return DbValidator(db_path)


@pytest.fixture(scope="session")
def token(base_url):
    response = AuthService(ApiClient(base_url)).get_token(config.CLIENT_ID, config.CLIENT_SECRET)
    assert response.status_code == 200, f"Could not get a token: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def anonymous_client(base_url):
    return ApiClient(base_url)


@pytest.fixture
def client(base_url, token):
    return ApiClient(base_url, token)


@pytest.fixture
def auth_api(anonymous_client):
    return AuthService(anonymous_client)


@pytest.fixture
def applicants(client):
    return ApplicantService(client)


@pytest.fixture
def applications(client):
    return ApplicationService(client)


@pytest.fixture
def new_applicant(applicants):
    """Factory: create an applicant (with optional overrides) and return its JSON."""
    def _create(**overrides):
        response = applicants.create(applicant_payload(**overrides))
        assert response.status_code == 201, response.text
        return response.json()
    return _create


@pytest.fixture
def new_application(applications):
    """Factory: create an application for an applicant and return its JSON."""
    def _create(applicant_id: int, **overrides):
        response = applications.create(application_payload(applicant_id, **overrides))
        assert response.status_code == 201, response.text
        return response.json()
    return _create
