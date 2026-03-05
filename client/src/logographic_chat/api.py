import httpx
from logographic_chat.auth import debug, error


class ChatAPI:
    def __init__(self, server_url: str, access_token: str):
        self.client = httpx.Client(
            base_url=server_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        debug("ChatAPI initialized", server=server_url)

    def list_rooms(self) -> list[dict]:
        debug("Fetching rooms list")
        resp = self.client.get("/api/rooms/")
        debug("Rooms response", status=resp.status_code)
        resp.raise_for_status()
        return resp.json()

    def get_messages(self, room_id: int, limit: int = 50) -> list[dict]:
        debug("Fetching messages", room_id=room_id)
        resp = self.client.get(f"/api/rooms/{room_id}/messages/")
        debug("Messages response", status=resp.status_code)
        resp.raise_for_status()
        return resp.json()

    def verify_token(self) -> bool:
        try:
            self.list_rooms()
            return True
        except httpx.HTTPStatusError as e:
            error("Token verification failed", status=e.response.status_code)
            return False
