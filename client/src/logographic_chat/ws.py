import json
import ssl
import websockets
from logographic_chat.auth import debug, error


class ChatSocket:
    def __init__(self, server_url: str, access_token: str):
        ws_scheme = "wss" if server_url.startswith("https") else "ws"
        host = server_url.replace("https://", "").replace("http://", "")
        self.base_ws_url = f"{ws_scheme}://{host}"
        self.token = access_token
        self.ws = None
        debug("ChatSocket initialized", ws_url=self.base_ws_url)

    async def connect(self, room_id: int):
        url = f"{self.base_ws_url}/ws/chat/{room_id}/?token={self.token}"
        debug("Connecting to WebSocket", url=url)

        # First try with strict SSL verification
        try:
            self.ws = await websockets.connect(url)
            debug("WebSocket connected", room_id=room_id)
            return
        except ssl.SSLCertVerificationError as ssl_error:
            debug("SSL verification failed, trying without verification", error=str(ssl_error))
            # Fall back to non-verifying SSL context
        except Exception as e:
            error("WebSocket connection failed", error=str(e))
            raise

        # Try again with SSL verification disabled
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self.ws = await websockets.connect(url, ssl=ssl_context)
            debug("WebSocket connected (without SSL verification)", room_id=room_id)
        except Exception as e:
            error("WebSocket connection failed even with SSL disabled", error=str(e))
            raise

    async def send(self, message: str):
        debug("Sending WebSocket message", length=len(message))
        await self.ws.send(json.dumps({"message": message}))

    async def receive(self):
        data = json.loads(await self.ws.recv())
        debug("Received WebSocket message", length=len(data))
        return data

    async def close(self):
        if self.ws:
            debug("Closing WebSocket")
            await self.ws.close()
