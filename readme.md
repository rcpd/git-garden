# Git-Garden

[![Python versions](https://img.shields.io/pypi/pyversions/genbadge.svg)](https://pypi.python.org/pypi/genbadge/)
![Build](https://github.com/rcpd/git-garden/actions/workflows/pr-pipeline.yml/badge.svg)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v0.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

## Installation

```
# installation is not required for normal use but can be done with
python -m pip install .
```

## Develop Installation

```
python -m pip install -e . # pip
uv sync --extra dev --frozen # uv (see [appendix.md](./appendix.md))
```

## Common Use Cases

```
# run with defaults: fetch & prune, report on local branches only
# --directory is the root of the directories being walked for git repos
# if --directory is not passed it will default to D:\dev (Windows) or ~ (Linux)
python -m git_garden --directory D:\dev

# attempt to fast-forward main/master (or --root) if behind
python -m git_garden --ff

# include or exclude directories matching a sub-string
# i.e. for D:\dev\MyProject & D:\dev\MyOtherProject
python -m git_garden --include MyProject --include MyOtherProject
python -m git_garden --exclude MyProject --exclude MyOtherProject

# attempt to delete orphaned local branches
# (branches with remote tracking where remote no longer exists)
python -m git_garden --delete

# see usage/syntax help
python -m git_garden --help
```