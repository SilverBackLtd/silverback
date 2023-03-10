import os
from pathlib import Path

import click
import uvicorn
from ape.cli import network_option


@click.group()
def cli():
    """Work with SilverBack applications in local context (using Ape)."""


@cli.command()
@network_option()
@click.argument("name", type=click.Path(exists=True))
def run(network, name):
    os.environ["SILVERBACK_NETWORK_CHOICE"] = network
    app_path = Path(name)
    os.environ["PYTHONPATH"] = str(app_path.parent)
    app_name = app_path.stem
    uvicorn.run(f"{app_name}:app")
