# Git-Garden

![Python](https://img.shields.io/badge/python-3.10-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Build](https://github.com/rcpd/git-garden/actions/workflows/pr-pipeline.yml/badge.svg?branch=main)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v1.json)](https://github.com/astral-sh/ruff)
[![mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

A simple Python git wrapper to help manage multi-project maintenance with automated fetching, pruning, fast-forwarding, deleting orphans and more!

## Installation

```
pip install git-garden
```

## Common Use Cases

```
# run with defaults: fetch & prune, report on local branches status only
# --dir is the root of the directories being walked for git repos
# if --dir is not passed it will default to the parent dir of project root
python -m git_garden --dir D:\dev

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