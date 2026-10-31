from framework.api_client import ApiClient


class ApplicationService:
    PATH = "/api/v1/applications"

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict):
        return self.client.post(self.PATH, json=payload)

    def get(self, application_id: int):
        return self.client.get(f"{self.PATH}/{application_id}")

    def determine(self, application_id: int):
        return self.client.post(f"{self.PATH}/{application_id}/determination")

    def notices(self, application_id: int):
        return self.client.get(f"{self.PATH}/{application_id}/notices")
