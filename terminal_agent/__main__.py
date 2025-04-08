import typer
from .ui import TerminalUI

app = typer.Typer()

@app.command()
def main():
    """Launch the Terminal Agent"""
    ui = TerminalUI()
    ui.run()

if __name__ == "__main__":
    app() 