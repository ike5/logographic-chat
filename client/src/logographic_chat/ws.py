import json
import websockets


class ChatSocket:
    def __init__(self, server_url: str, access_token: str):
        ws_scheme = "wss" if server_url.startswith("https") else "ws"
        host = server_url.replace("https://", "").replace("http://", "")
        self.base_ws_url = f"{ws_scheme}://{host}"
        self.token = access_token
        self.ws = None

    async def connect(self, room_id: int):
        url = f"{self.base_ws_url}/ws/chat/{room_id}/?token={self.token}"
        self.ws = await websockets.connect(url)

    async def send(self, message: str):
        await self.ws.send(json.dumps({"message": message}))

    async def receive(self):
        return json.loads(await self.ws.recv())

    async def close(self):
        if self.ws:
            await self.ws.close()
