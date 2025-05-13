import asyncio
from rich.console import Console, Group
from rich.panel import Panel
from rich.layout import Layout
from rich.markdown import Markdown
from rich import box
from rich.prompt import Prompt
from rich.rule import Rule
from .dockerClient import DockerExecution
from .agent import AIAgent
import asyncio
import os
from rich.syntax import Syntax
from rich.table import Table


# ui.py has own convo history to avoid displaying metadata - cleaner responses
# Go into that and make some changes to format responses better with regards to docker output and confirmation that tool ran
# agent.py convo history has tool calls + responses 

class TerminalUI:
    def __init__(self):
        self.console = Console()
        self.messages = ["Welcome to Terminal Agent! Type your message below."]
        self.docker_messages = ["Docker Container Output"]
        self.layout = Layout()
        self.setup_layout()
        self.docker_mode = False  # 
        self.agent = None

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
        rendered = []
        if mode_indicator:
            rendered.append(Markdown(mode_indicator))
        for msg in self.docker_messages:
            if isinstance(msg, tuple) and msg[0] == "panel":
                rendered.append(msg[1])
            else:
                rendered.append(Markdown(str(msg)))
        return Panel(
            Group(*rendered),
            title="[bold green]Docker Container[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )

    def format_tool_execution(self, tool_output):
        # If it's a dict with exit_code and output, format nicely
        if isinstance(tool_output, dict) and 'exit_code' in tool_output and 'output' in tool_output:
            exit_code = tool_output['exit_code']
            output = tool_output['output']
            exit_status = (
                f"[green]Exit code: {exit_code}[/green]" if exit_code == 0
                else f"[red]Exit code: {exit_code}[/red]"
            )
            # If output looks like a file list, show as a table
            if '\n' in output and all('/' not in f for f in output.split()):

                table = Table(show_header=False, box=box.SIMPLE)

                for fname in output.split():
                    table.add_row(fname)
                content = table
            else:
                content = output
            return Panel(
                Group(
                    f"{exit_status}",
                    content
                ),
                title="[bold magenta]Tool Execution[/bold magenta]",
                border_style="magenta",
                padding=(1, 2)
            )
        # If it's a string, just return as Markdown
        return Markdown(str(tool_output))

    def format_tool_panel(self, tool_name, details, content=None, style="magenta"):
        md = ""

        for k, v in details.items():
            md += f"- **{k}**: {v}\n"
        
        if content:
            md += f"\n{content}\n"
        
        return Panel(Markdown(md), title=f"[bold {style}]{tool_name}[/bold {style}]", border_style=style)

    async def run(self):
        docker_client = DockerExecution()
        docker_client.start_container()
        self.agent = AIAgent(docker_client)
        self.docker_messages.append("Docker Container Output")
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
                    exit_code, output = docker_client.container.exec_run(f"/bin/bash -c '{user_input}'")
                    result = output.decode('utf-8')
                    panel = self.format_docker_output(user_input, result, exit_code)
                    self.docker_messages.append(("panel", panel))
                except Exception as e:
                    self.docker_messages.append(f"$ {user_input}\nError: {str(e)}")
            elif not self.docker_mode:
                response = await self.agent.process_input(user_input)
                tool_output = response.get('docker_output')
                if tool_output:
                    
                    if isinstance(tool_output, dict) and 'exit_code' in tool_output:
                        panel = self.format_tool_panel(
                            "RunCommand",
                            {"Exit code": tool_output['exit_code']},
                            tool_output['output'],
                            style="magenta"
                        )
                        self.docker_messages.append(("panel", panel))
                    else:
                        self.docker_messages.append(("panel", self.format_tool_panel("Tool", {}, str(tool_output))))
                else:
                    self.messages.extend([
                        f"You: {user_input}",
                        f"Agent: {response['response_text']}"
                    ])


        