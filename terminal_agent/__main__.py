import typer
import asyncio
from .ui import TerminalUI

app = typer.Typer()

@app.command()
def main():
    ui = TerminalUI()
    asyncio.run(ui.run())

if __name__ == "__main__":
    app() 