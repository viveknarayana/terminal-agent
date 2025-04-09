from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.markdown import Markdown
from rich import box
from rich.prompt import Prompt
import os

class TerminalUI:
    def __init__(self):
        self.console = Console()
        self.messages = ["Type Below"]
        self.docker_messages = ["Docker Container Output"]
        self.layout = Layout()
        self.setup_layout()

    def setup_layout(self):
        # Double layout for terminal and docker
        self.layout.split_row(
            Layout(name="terminal", ratio=1),
            Layout(name="docker", ratio=1)
        )

    def display_terminal_panel(self):
        content = "\n\n".join(self.messages)
        return Panel(
            Markdown(content),
            title="[bold blue]Terminal Interaction[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2)
        )

    def display_docker_panel(self):
        content = "\n\n".join(self.docker_messages)
        return Panel(
            Markdown(content),
            title="[bold green]Docker Container[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )

    def run(self):
        # Main UI loop
        while True:
            # Clear screen using os.system
            os.system('cls' if os.name == 'nt' else 'clear')
            
            self.layout["terminal"].update(self.display_terminal_panel())
            self.layout["docker"].update(self.display_docker_panel())
            
            # Display layout once
            self.console.print(self.layout)
            
            # Get input
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
            
            if user_input.lower() == "exit":
                self.console.print("[yellow]Goodbye![/yellow]")
                break
            
            # Update messages
            self.messages.extend([
                f"You: {user_input}",
                f"Agent: I received your message: {user_input}"
            ]) 