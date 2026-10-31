from framework.api_client import ApiClient


class ApplicantService:
    PATH = "/api/v1/applicants"

    def __init__(self, client: ApiClient):
        self.client = client

    def create(self, payload: dict):
        return self.client.post(self.PATH, json=payload)

    def get(self, applicant_id: int):
        return self.client.get(f"{self.PATH}/{applicant_id}")
