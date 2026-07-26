"""
FastCOAP CLI

    fastcoap run main:app
    fastcoap run main:app --host 0.0.0.0 --port 5683 --reload
    fastcoap routes main:app
"""
from __future__ import annotations
import asyncio
import importlib
import sys
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="fastcoap",
    help="FastCOAP — a modern, high-performance Python framework for building CoAP applications and APIs",
    add_completion=False,
)
console = Console()


def _import_app(app_string: str):
    if ":" not in app_string:
        typer.echo(f"❌  Invalid app string '{app_string}'. Use module:attribute", err=True)
        raise typer.Exit(1)

    module_path, attr = app_string.rsplit(":", 1)
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        typer.echo(f"❌  Cannot import module '{module_path}': {e}", err=True)
        raise typer.Exit(1)

    try:
        return getattr(module, attr)
    except AttributeError:
        typer.echo(f"❌  Module '{module_path}' has no attribute '{attr}'", err=True)
        raise typer.Exit(1)


# ── top-level function so multiprocessing/spawn can pickle it ────────────────

def _reload_worker(app_string: str, host: str, port: int) -> None:
    """Entry point for the watchfiles worker process."""
    import asyncio as _asyncio
    import importlib as _importlib
    import sys as _sys
    from pathlib import Path as _Path

    cwd = str(_Path.cwd())
    if cwd not in _sys.path:
        _sys.path.insert(0, cwd)

    module_path, attr = app_string.rsplit(":", 1)
    module = _importlib.import_module(module_path)
    coap_app = getattr(module, attr)
    _asyncio.run(coap_app.serve(host=host, port=port))


@app.command()
def run(
    app_string: str = typer.Argument(..., metavar="MODULE:APP", help="e.g. main:app"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host"),
    port: int = typer.Option(5683, "--port", "-p", help="CoAP UDP port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on file changes"),
    log_level: str = typer.Option("info", "--log-level", help="Logging level"),
):
    """Start a FastCOAP server."""
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
    )

    console.print(
        Panel.fit(
            f"[bold cyan]FastCOAP[/bold cyan]  🛰️\n"
            f"[green]CoAP:[/green]  coap://{host}:{port}",
            title="[bold]Starting server[/bold]",
            border_style="cyan",
        )
    )

    if reload:
        _run_with_reload(app_string, host, port)
    else:
        coap_app = _import_app(app_string)
        asyncio.run(coap_app.serve(host=host, port=port))


def _run_with_reload(app_string: str, host: str, port: int) -> None:
    try:
        from watchfiles import run_process
    except ImportError:
        typer.echo("❌  Install 'watchfiles': uv add watchfiles", err=True)
        raise typer.Exit(1)

    console.print("[yellow]⚡ Reload mode active — watching for file changes…[/yellow]")
    # Pass args separately — run_process forwards them to _reload_worker.
    # _reload_worker is a module-level function, so spawn can pickle it.
    run_process(".", target=_reload_worker, args=(app_string, host, port))


@app.command()
def routes(
    app_string: str = typer.Argument(..., metavar="MODULE:APP"),
):
    """List all registered routes."""
    from rich.table import Table

    coap_app = _import_app(app_string)
    table = Table(title="Registered Routes", header_style="bold cyan")
    table.add_column("Method", style="green")
    table.add_column("Path", style="white")
    table.add_column("Handler", style="yellow")
    table.add_column("Tags")

    for route in coap_app.routes:
        table.add_row(
            route.method,
            route.path,
            route.handler.__name__,
            ", ".join(route.tags),
        )
    console.print(table)


if __name__ == "__main__":
    app()