from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static, Header, Footer, Input
from .dockerClient import DockerExecution
from .agent import AIAgent
from rich.panel import Panel
from rich.text import Text

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.docker_mode = False
        self.docker_client = None
        self.agent = None
        self.system_prompt = (
            "You are an AI terminal agent. You can call tools in succession to accomplish multi-step user requests in a Docker container. "
            "For each user request, decide if you should call a tool or respond with text. "
            "If the request requires multiple actions, call the necessary tools one after another until all steps are complete, then respond with text. "
            "Never output tool call instructions as text. If you need to use a tool, always use the tool call API. "
            "Only respond with text when you are done with all tool calls needed for the user's request."
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield TerminalPanel(id="terminal_panel")
            yield DockerPanel(id="docker_panel")
        yield Input(placeholder="Type your command and press Enter...", id="input")
        yield Footer()

    async def on_mount(self):
        self.query_one("#terminal_panel").focus()
        # Initialize Docker and agent
        self.docker_client = DockerExecution()
        self.docker_client.start_container()
        self.agent = AIAgent(self.docker_client)
        await self.query_one("#terminal_panel", TerminalPanel).add_message("Welcome to Terminal Agent! Type your message below.")
        await self.query_one("#docker_panel", DockerPanel).add_message("Docker Container Output")

    def action_switch_panel(self):
        focused = self.focused
        panels = [
            self.query_one("#terminal_panel"),
            self.query_one("#docker_panel")
        ]
        next_panel = panels[1] if focused is panels[0] else panels[0]
        self.set_focus(next_panel)

    def format_tool_output_panel(self, tool, args, output):
        content = f"Tool: {tool}\nArgs: {args}\n\n{output}"
        return Panel(
            Text(str(content), style="white", markup=False),
            title="[bold magenta]TOOL OUTPUT[/bold magenta]",
            border_style="magenta",
            padding=(1, 2)
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        terminal_panel = self.query_one("#terminal_panel", TerminalPanel)
        docker_panel = self.query_one("#docker_panel", DockerPanel)
        input_widget = self.query_one("#input", Input)
        input_widget.value = ""
        input_widget.focus()

        if user_input.lower() == "exit":
            if self.docker_mode:
                self.docker_mode = False
                await terminal_panel.add_message("Agent: Exited Docker input mode")
                return
            else:
                await terminal_panel.add_message("[yellow]Goodbye! (Press q to quit)[/yellow]")
                return
        if user_input.lower() == "docker":
            self.docker_mode = True
            await terminal_panel.add_message(f"You: {user_input}")
            await terminal_panel.add_message("Agent: Entering Docker input mode. Type 'exit' to return to normal mode.")
            return
        if self.docker_mode and self.docker_client and self.docker_client.container:
            try:
                exit_code, output = self.docker_client.container.exec_run(f"/bin/bash -c '{user_input}'")
                result = output.decode('utf-8')
                await docker_panel.add_message(f"$ {user_input}\n{result}")
                await terminal_panel.add_message(f"You: {user_input}")
            except Exception as e:
                await docker_panel.add_message(f"$ {user_input}\nError: {str(e)}")
                await terminal_panel.add_message(f"You: {user_input}")
        else:
            await terminal_panel.add_message(f"You: {user_input}")
            async for event in self.agent.process_input_stream(user_input):
                if event["type"] == "tool":
                    panel = self.format_tool_output_panel(event['tool'], event['args'], event['output'])
                    await docker_panel.mount(Static(panel, markup=False))
                elif event["type"] == "text":
                    await terminal_panel.add_message(f"Agent: {event['response']}")

if __name__ == "__main__":
    TerminalTUI().run()
