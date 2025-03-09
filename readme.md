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
# if --dir is not passed it will default to the current working directory
git-garden --dir D:\dev

# attempt to fast-forward main/master (or --root) if behind
git-garden --ff

# include or exclude directories matching a sub-string
# i.e. for D:\dev\MyProject & D:\dev\MyOtherProject
git-garden --include MyProject --include MyOtherProject
git-garden --exclude MyProject --exclude MyOtherProject

# attempt to delete orphaned local branches
# (branches with remote tracking where remote no longer exists)
git-garden --delete

# see usage/syntax help
git-garden --help
```