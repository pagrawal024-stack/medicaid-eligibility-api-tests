"""Test configuration, read from environment variables.

BASE_URL      Run against an already running API instead of starting one.
DB_PATH       SQLite file to validate against (required with BASE_URL).
API_CLIENT_ID / API_CLIENT_SECRET   Credentials for /auth/token.
"""
import os

BASE_URL = os.getenv("BASE_URL")
DB_PATH = os.getenv("DB_PATH")
CLIENT_ID = os.getenv("API_CLIENT_ID", "qa-client")
CLIENT_SECRET = os.getenv("API_CLIENT_SECRET", "qa-secret")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
MAX_RESPONSE_TIME_SECONDS = float(os.getenv("MAX_RESPONSE_TIME_SECONDS", "2"))
