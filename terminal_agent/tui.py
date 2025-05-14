from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static, Header, Footer, Input

class TerminalPanel(VerticalScroll):
    can_focus = True
    async def add_message(self, text):
        await self.mount(Static(text))
        self.scroll_end(animate=False)

class DockerPanel(VerticalScroll):
    can_focus = True
    async def add_message(self, text):
        await self.mount(Static(text))
        self.scroll_end(animate=False)

class TerminalTUI(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("tab", "switch_panel", "Switch Panel"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield TerminalPanel(id="terminal_panel")
            yield DockerPanel(id="docker_panel")
        yield Input(placeholder="Type your command and press Enter...", id="input")
        yield Footer()

    async def on_mount(self):
        self.query_one("#terminal_panel").focus()

    def action_switch_panel(self):
        focused = self.focused
        panels = [
            self.query_one("#terminal_panel"),
            self.query_one("#docker_panel")
        ]
        next_panel = panels[1] if focused is panels[0] else panels[0]
        self.set_focus(next_panel)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value
        await self.query_one("#terminal_panel", TerminalPanel).add_message(f"You: {user_input}")
        await self.query_one("#docker_panel", DockerPanel).add_message(f"[Echo to Docker] {user_input}")
        event.input.value = ""
        self.query_one("#input", Input).focus()

if __name__ == "__main__":
    TerminalTUI().run()
