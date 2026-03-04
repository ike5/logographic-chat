from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Footer, Input, Static
from .api import ChatAPI
from .ws import ChatSocket


class MessageView(Static):
    def __init__(self, username: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.content = content

    def render(self):
        return f"[bold]{self.username}[/bold]  {self.content}"


class ChatApp(App):
    CSS = """
    #messages { height: 1fr; }
    #input { dock: bottom; }
    """
    BINDINGS = [("escape", "quit", "Quit")]

    def __init__(self, server_url: str, access_token: str, username: str):
        super().__init__()
        self.server_url = server_url
        self.access_token = access_token
        self.username = username
        self.api = ChatAPI(server_url, access_token)
        self.socket = ChatSocket(server_url, access_token)
        self.current_room_id = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="input")
        yield Footer()

    async def on_mount(self):
        rooms = self.api.list_rooms()
        if not rooms:
            self.query_one("#messages").mount(MessageView("system", "No rooms available."))
            return
        self.current_room_id = rooms[0]["id"]
        self.title = f"# {rooms[0]['name']}"

        messages = self.api.get_messages(self.current_room_id)
        container = self.query_one("#messages")
        for msg in messages:
            await container.mount(MessageView(msg["username"], msg["content"]))

        await self.socket.connect(self.current_room_id)
        self.run_worker(self.listen_for_messages())

    async def listen_for_messages(self):
        try:
            while True:
                data = await self.socket.receive()
                container = self.query_one("#messages")
                await container.mount(MessageView(data["username"], data["message"]))
                container.scroll_end()
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if text and self.socket:
            await self.socket.send(text)
            event.input.value = ""
