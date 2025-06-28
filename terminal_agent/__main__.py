import typer
import asyncio
from .tui import TerminalTUI

app = typer.Typer()

@app.command()
def main():
    app = TerminalTUI()
    app.run()

if __name__ == "__main__":
    app() 