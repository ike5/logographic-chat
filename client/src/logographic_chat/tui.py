from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Header, Footer, Input, Static, ListView, ListItem, Label
from logographic_chat.api import ChatAPI
from logographic_chat.auth import clear_credentials, debug, error, info
from logographic_chat.ws import ChatSocket


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
        ("ctrl+l", "logout", "Logout"),
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
        debug("ChatApp initialized", server=server_url, username=username)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ListView(id="sidebar")
        yield VerticalScroll(id="messages")
        yield Input(placeholder="Type a message...", id="input")
        yield Footer()

    async def on_mount(self):
        debug("TUI mounting, fetching rooms")
        try:
            self.rooms = self.api.list_rooms()
            debug("Fetched rooms", count=len(self.rooms))
            sidebar = self.query_one("#sidebar", ListView)
            for room in self.rooms:
                await sidebar.append(ListItem(Label(room["name"]), id=f"room-{room['id']}"))

            if not self.rooms:
                await self.query_one("#messages", VerticalScroll).mount(
                    MessageView("system", "No rooms available.")
                )
                return

            await self._join_room(self.rooms[0])
        except Exception as e:
            error("Failed to load rooms", error=str(e))
            raise

    async def _join_room(self, room: dict):
        debug("Joining room", room_id=room["id"], room_name=room["name"])
        if self.socket.ws:
            await self.socket.close()

        self.current_room_id = room["id"]
        self.title = f"# {room['name']}"

        container = self.query_one("#messages", VerticalScroll)
        await container.remove_children()

        try:
            messages = self.api.get_messages(self.current_room_id)
            debug("Fetched messages", count=len(messages))
            for msg in messages:
                await container.mount(MessageView(msg["username"], msg["content"]))
            container.scroll_end()
        except Exception as e:
            error("Failed to fetch messages", error=str(e))

        try:
            await self.socket.connect(self.current_room_id)
            info("WebSocket connected", room_id=self.current_room_id)
            self.run_worker(self.listen_for_messages(), group="ws", exclusive=True)
        except Exception as e:
            error("WebSocket connection failed", error=str(e))
            raise

    def action_logout(self):
        info("Logging out")
        clear_credentials()
        self.exit()

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
        debug("Starting message listener")
        try:
            while True:
                data = await self.socket.receive()
                debug("Received message", username=data.get("username"), message=data.get("message")[:50])
                container = self.query_one("#messages", VerticalScroll)
                await container.mount(MessageView(data["username"], data["message"]))
                container.scroll_end()
        except Exception as e:
            error("Message listener crashed", error=str(e))

    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if text and self.socket:
            await self.socket.send(text)
            event.input.value = ""
