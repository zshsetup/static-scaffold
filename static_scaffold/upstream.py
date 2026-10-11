"""Writes the workflows that follow new releases of the upstream project of a `-static` repo."""

from __future__ import annotations

from pathlib import Path

import msgspec

from static_scaffold.models import UpstreamEntry

PACKAGE = Path(__file__).resolve().parent
WORKFLOWS = ("upstream-update.yml", "upstream-release.yml")


def load_table() -> dict[str, UpstreamEntry]:
    """Returns the upstream entry of each known `-static` repo by its name."""
    return msgspec.toml.decode(
        (PACKAGE / "upstream.toml").read_bytes(), type=dict[str, UpstreamEntry]
    )


def write_workflows(root: Path, name: str, entry: UpstreamEntry) -> None:
    """Writes the update and the release workflow of `name` into the repo at `root`."""
    values = {
        "NAME": name,
        "DIR": entry.dir,
        "URL": entry.url,
        "PATTERN": entry.pattern,
        "SED": entry.release_sed,
    }
    target = root / ".github/workflows"
    target.mkdir(parents=True, exist_ok=True)
    for workflow in WORKFLOWS:
        text = (PACKAGE / "templates" / workflow).read_text()
        for key, value in values.items():
            text = text.replace(f"__{key}__", value)
        (target / workflow).write_text(text)
