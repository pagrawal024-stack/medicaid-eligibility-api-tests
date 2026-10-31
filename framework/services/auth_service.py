from framework.api_client import ApiClient


class AuthService:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_token(self, client_id: str, client_secret: str):
        return self.client.post(
            "/auth/token", json={"client_id": client_id, "client_secret": client_secret}
        )
