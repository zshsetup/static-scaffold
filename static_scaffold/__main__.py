"""Command-line interface of static-scaffold."""

from __future__ import annotations

if __name__ == "__main__":
    import doctyper

    from static_scaffold.cli import new, upstream

    app = doctyper.DocTyper(help=__doc__)
    app.command()(new)
    app.command()(upstream)
    app(prog_name="static-scaffold")
