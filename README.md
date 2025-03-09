# Git-Garden

[![PyPI](https://img.shields.io/pypi/v/git-garden.svg)](https://pypi.org/project/git-garden/)
![Python](https://img.shields.io/pypi/pyversions/git-garden)
![Build](https://github.com/rcpd/git-garden/actions/workflows/pr-pipeline.yml/badge.svg?branch=main)
[![Docs](https://readthedocs.org/projects/git-garden/badge)](https://git-garden.readthedocs.io/latest/)
[![Coverage](https://coveralls.io/repos/github/c0ff33-dev/git-garden/badge.svg?branch=main)](https://coveralls.io/github/c0ff33-dev/git-garden?branch=main)

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