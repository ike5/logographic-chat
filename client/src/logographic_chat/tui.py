from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Label
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
    #sidebar {
        width: 24;
        dock: left;
        display: none;
        background: $panel;
        border-right: solid $primary;
        padding: 0 1;
    }
    #sidebar.visible { display: block; }
    #messages { height: 1fr; }
    #input { dock: bottom; }
    """
    BINDINGS = [
        ("ctrl+r", "toggle_sidebar", "Rooms"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, server_url: str, access_token: str, username: str):
        super().__init__()
        self.server_url = server_url
        self.access_token = access_token
        self.username = username
        self.api = ChatAPI(server_url, access_token)
        self.socket = ChatSocket(server_url, access_token)
        self.current_room_id = None
        self.rooms: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ListView(id="sidebar")
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="input")
        yield Footer()

    async def on_mount(self):
        self.rooms = self.api.list_rooms()
        sidebar = self.query_one("#sidebar", ListView)
        for room in self.rooms:
            await sidebar.append(ListItem(Label(room["name"]), id=f"room-{room['id']}"))

        if not self.rooms:
            await self.query_one("#messages", VerticalScroll).mount(
                MessageView("system", "No rooms available.")
            )
            return

        await self._join_room(self.rooms[0])

    async def _join_room(self, room: dict):
        if self.socket.ws:
            await self.socket.close()

        self.current_room_id = room["id"]
        self.title = f"# {room['name']}"

        container = self.query_one("#messages", VerticalScroll)
        await container.remove_children()

        for msg in self.api.get_messages(self.current_room_id):
            await container.mount(MessageView(msg["username"], msg["content"]))
        container.scroll_end()

        await self.socket.connect(self.current_room_id)
        self.run_worker(self.listen_for_messages(), group="ws", exclusive=True)

    def action_toggle_sidebar(self):
        sidebar = self.query_one("#sidebar", ListView)
        sidebar.toggle_class("visible")
        if sidebar.has_class("visible"):
            sidebar.focus()
        else:
            self.query_one("#input", Input).focus()

    async def on_list_view_selected(self, event: ListView.Selected):
        room_id = int(event.item.id.split("-")[1])
        room = next(r for r in self.rooms if r["id"] == room_id)
        self.action_toggle_sidebar()
        await self._join_room(room)
        self.query_one("#input", Input).focus()

    async def listen_for_messages(self):
        try:
            while True:
                data = await self.socket.receive()
                container = self.query_one("#messages", VerticalScroll)
                await container.mount(MessageView(data["username"], data["message"]))
                container.scroll_end()
        except Exception:
            pass

    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if text and self.socket:
            await self.socket.send(text)
            event.input.value = ""
