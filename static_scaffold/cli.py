"""Subcommands of the CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import doctyper

from static_scaffold.scaffold import load_config, scaffold, write_summary
from static_scaffold.upstream import write_workflows


def new(
    config: Annotated[Path, doctyper.Argument(help="TOML description of the repo.")],
    output: Annotated[Path, doctyper.Option(help="Directory to create the repo in.")] = Path(),
    org: Annotated[str, doctyper.Option(help="GitHub organization of the repo.")] = "zshsetup",
) -> None:
    """Creates a `-static` repo from its TOML description with copier."""
    write_summary(scaffold(load_config(config), output.resolve(), org))


def upstream(
    root: Annotated[Path, doctyper.Argument(help="Checkout of the `-static` repo.")],
    name: Annotated[str, doctyper.Argument(help="Name of the project, e.g. tmux.")],
) -> None:
    """Writes the workflows that open a pull request when upstream has a new release."""
    write_workflows(root, name)
