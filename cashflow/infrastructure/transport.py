import httpx

from cashflow.application.ports import PermanentDeliveryError


class HttpEventTransport:
    def __init__(self, client: httpx.Client, url: str, token: str):
        self.client, self.url, self.token = client, url, token

    def send(self, event):
        response = self.client.post(
            self.url + "/internal/events",
            json=event,
            headers={"Authorization": "Bearer " + self.token},
        )
        if response.status_code in (400, 409, 413, 422):
            raise PermanentDeliveryError("event rejected")
        response.raise_for_status()
