import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.markdown import Markdown
from rich import box
from rich.prompt import Prompt
from rich.rule import Rule
from .dockerClient import DockerExecution
import os


class TerminalUI:
    def __init__(self):
        self.console = Console()
        self.messages = ["Welcome to Terminal Agent! Type your message below."]
        self.docker_messages = ["Docker Container Output"]
        self.layout = Layout()
        self.setup_layout()
        self.docker_mode = False  # 

    def setup_layout(self):
        # Double layout for terminal and docker
        self.layout.split_row(
            Layout(name="terminal", ratio=1),
            Layout(name="docker", ratio=1)
        )

    def display_terminal_panel(self):
        content = "\n\n".join(self.messages) + "\n\nYou: "
        return Panel(
            content,
            title="[bold blue]Terminal Interaction[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2)
        )

    def display_docker_panel(self):
        mode_indicator = "[bold red](DOCKER INPUT MODE)[/bold red]\n\n" if self.docker_mode else ""
        content = mode_indicator + "\n\n".join(self.docker_messages)
        return Panel(
            Markdown(content),
            title="[bold green]Docker Container[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )

    def run(self):
        docker_client = DockerExecution()
        docker_client.start_container()
        self.docker_messages.append("Starting Docker container...")
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            self.layout["terminal"].update(self.display_terminal_panel())
            self.layout["docker"].update(self.display_docker_panel())
            
            self.console.print(self.layout)
            
            prompt = "Docker > " if self.docker_mode else "You: "
            user_input = input(prompt).strip()
            
            if user_input.lower() == "exit":
                if self.docker_mode:
                    self.docker_mode = False
                    self.messages.append("Agent: Exited Docker input mode")
                    continue
                else:
                    self.console.print("[yellow]Goodbye![/yellow]")
                    break

            if user_input.lower() == "docker":
                self.docker_mode = True
                self.messages.extend([
                f"You: {user_input}",
                f"Agent: Entering Docker input mode. Type 'exit' to return to normal mode."
                ])
                continue
            
            if self.docker_mode and docker_client and docker_client.container:
                try:
                    # KEEP THIS FOR USER TO ACCESS DOCKER CONTAINER WITHOUT USE OF AGENT (check files and stuff)
                    # TMR ADD MORE TOOLS IN DOCKER FILE AND FORMAT IT SO ITS USABLE WITH ANTHROPICSDK
                    exit_code, output = docker_client.container.exec_run(f"/bin/bash -c '{user_input}'")
                    result = output.decode('utf-8')
                    self.docker_messages.append(f"$ {user_input}\n{result}")
                except Exception as e:
                    self.docker_messages.append(f"$ {user_input}\nError: {str(e)}")

            elif not self.docker_mode:
                self.messages.extend([
                f"You: {user_input}",
                f"Agent: I received your message: {user_input}"
                ])