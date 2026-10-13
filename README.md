# static-scaffold

Generates the `<name>-static` repos of zshsetup: vendored upstream projects as shallow submodules
under `vendor/`, a `build.sh` that builds with [zig](https://ziglang.org) as the C toolchain, smoke
tests, CI, and a release workflow. It also writes the workflows that open a pull request when
upstream publishes a new release.

## Prerequisites

- `uv`, which runs `copier` for the base files from
  [audivir/copier-template](https://github.com/audivir/copier-template)
- `git`, and `gh` to publish the created repo

## Installation

```shell
git clone https://github.com/zshsetup/static-scaffold
cd static-scaffold
uv sync
```

## Usage

Describe a project in `configs/<name>.toml`, see `configs/tmux.toml`, then create the repo:

```shell
uv run python -m static_scaffold new configs/tmux.toml --output ~/repos
```

The repo is created in `~/repos/tmux-static` with the submodules cloned. Review it, then publish
it with `gh repo create zshsetup/tmux-static --public --source . --push`.

`new` also writes the workflows that open a pull request when upstream publishes a new release,
using the `[upstream_tags]` table of the config. To rewrite them in an existing checkout, e.g. after
a change of the templates, run:

```shell
uv run python -m static_scaffold upstream ~/repos/tmux-static tmux
```

The tag patterns of all repos, also those without a config, are listed in
`static_scaffold/upstream.toml`. The workflows
need an `UPDATE_TOKEN` secret, a token of a user that may push to the repo and create releases,
because pull requests and releases of the default token start no workflows.

## Keeping the binaries small

The released archives are downloaded by every user, so a config should keep them small:

- Compile with `-ffunction-sections -fdata-sections`, link with `-Wl,--gc-sections` (`-Wl,-dead_strip`
  on macOS) and `-s`, as `configs/openssh.toml` does.

- Build the libraries without what the program does not use, e.g. OpenSSL without TLS, DSA, and
  the legacy ciphers.

- Never ship a copy of a binary under a second name, use a symlink (`unpigz` links to `pigz`). The
  archives keep symlinks, and the spec of pmg reaches them with `links`.

- Link a project with several programs into a single multi-call binary, as BusyBox does, when each
  program would otherwise carry its own copy of a large static library. The binary picks its tool
  from the name it is run as, and the other names are symlinks to it. `configs/openssh.toml` does
  this and shrinks the suite from about 62 MB (24 MB archived) to 7.6 MB (3.2 MB), the recipe is:

  1. Partial-link the objects of each program with the parts of the project library it needs
     (`ld -r ... --start-group -lssh ... --end-group`), as the programs define globals with the same
     names, and the library calls functions that each program defines in its own way.
  1. Rename `main` to a name of its own (`objcopy --redefine-sym`, or `-Dmain=...` when compiling
     the file of `main` where there is no `objcopy`, e.g. macOS) and make every other symbol of the
     object local (`objcopy --keep-global-symbol`, `ld -r -exported_symbol` and `nmedit -s`).
  1. Link all of them once with a small dispatcher `main` that looks at `basename(argv[0])`.
  1. Check with the smoke tests that the programs find each other by name (`PATH`, symlinks), also
     those that a program starts itself, like `sshd` with `sshd-session`.

  It is feasible when the programs are built from separate objects, and not worth it for a single
  binary, or when the extra programs are small and share no large library.

## License

MIT
