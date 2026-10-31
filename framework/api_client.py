"""Thin HTTP client shared by every service object.

Keeps one requests.Session, adds the bearer token, applies a timeout and logs
every call, so a failing test shows exactly what was sent and received.
"""
import json
import logging

import requests

from framework import config

log = logging.getLogger("api")


class ApiClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if token:
            self.set_token(token)

    def set_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"

    def clear_token(self) -> None:
        self.session.headers.pop("Authorization", None)

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", config.REQUEST_TIMEOUT_SECONDS)
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, **kwargs)
        log.info(
            "%s %s -> %s (%.0f ms)\n  request: %s\n  response: %s",
            method, path, response.status_code,
            response.elapsed.total_seconds() * 1000,
            json.dumps(kwargs.get("json"), ensure_ascii=False) if "json" in kwargs else "-",
            response.text[:1000],
        )
        return response

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)
