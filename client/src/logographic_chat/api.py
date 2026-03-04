import httpx


class ChatAPI:
    def __init__(self, server_url: str, access_token: str):
        self.client = httpx.Client(
            base_url=server_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def list_rooms(self) -> list[dict]:
        resp = self.client.get("/api/rooms/")
        resp.raise_for_status()
        return resp.json()

    def get_messages(self, room_id: int, limit: int = 50) -> list[dict]:
        resp = self.client.get(f"/api/rooms/{room_id}/messages/")
        resp.raise_for_status()
        return resp.json()

    def verify_token(self) -> bool:
        try:
            self.list_rooms()
            return True
        except httpx.HTTPStatusError:
            return False
