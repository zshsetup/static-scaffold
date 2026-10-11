"""Models of the TOML files of this package."""

from __future__ import annotations

import msgspec


class Vendor(msgspec.Struct):
    """Stores a vendored project, checked out at a tag or a commit."""

    dir: str
    url: str
    tag: str = ""
    commit: str = ""


class Project(msgspec.Struct):
    """Stores an upstream project for the license notices."""

    name: str
    url: str
    copyright: str
    license: str


class Config(msgspec.Struct):
    """Stores the description of a `-static` repo."""

    name: str
    bin: str
    description: str
    upstream: str
    tag: str
    license_short: str
    outputs: str
    build: str
    version_cmd: str
    tests: str
    vendor: list[Vendor]
    project: list[Project]
    prereq: str = ""
    extra: str = ""
    apt: list[str] = []
    brew: list[str] = []
    dirs: str = "bin share"
    ncurses: bool = False
    macos_only: bool = False
    """Whether the project only builds on macOS, which drops the Linux jobs."""


class UpstreamEntry(msgspec.Struct):
    """Stores where to look for new upstream versions of a project."""

    dir: str
    url: str
    pattern: str
    """Extended regular expression of the tags that count as stable releases."""
    release_sed: str = ""
    """The sed script that turns an upstream tag into the release tag of the repo."""
