"""Subcommands of the CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import doctyper

from static_scaffold.scaffold import load_config, scaffold, write_summary
from static_scaffold.upstream import load_table, write_workflows


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
    """Rewrites the upstream workflows of an existing repo, e.g. after a change of the templates."""
    write_workflows(root, name, load_table()[name])
