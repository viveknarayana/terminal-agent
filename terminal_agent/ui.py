from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from rich.prompt import Prompt

class TerminalUI:
    def __init__(self):
        self.console = Console()
        self.messages = ["Type below"]

    def display_messages(self):
        # For conversation history
        content = "\n\n".join(self.messages)
        self.console.print(Panel(
            Markdown(content),
            title="[bold blue]Terminal Agent[/bold blue]",
            border_style="blue",
            box=box.ROUNDED,
            padding=(1, 2)
        ))

    def run(self):
        # Loop
        while True:
            self.console.clear()
            self.display_messages()
            
            # Get input
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
            
            if user_input.lower() == "exit":
                self.console.print("[yellow]Goodbye![/yellow]")
                break
            
            # Shows update - echo back for now
            self.messages.extend([
                f"You: {user_input}",
                f"Agent: I received your message: {user_input}"
            ]) 