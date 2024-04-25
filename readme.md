# Git-Garden

## Installation

```
# typing-extensions only required on <= 3.9
# otherwise no install required
python -m pip install -r requirements.txt
```

## Develop Installation

```
python -m pip install -r dev-requirements.txt
```

## Common Use Cases

```
# run with defaults: fetch & prune, report on local branches only
# --directory is the root of the directories being walked for git repos
# if --directory is not passed it will default to D:\dev (Windows) or ~ (Linux)
python -m git_garden --directory D:\dev

# attempt to fast-forward main/master if behind
python -m git_garden --ff

# include or exclude directories matching a sub-string
# i.e. for D:\dev\MyProject & D:\dev\MyOtherProject
python -m git_garden --include MyProject --include MyOtherProject
python -m git_garden --exclude MyProject --exclude MyOtherProject

# skip reporting basic current/ahead/behind status
python -m git_garden --quiet

# attempt to delete orphaned local branches
# (branches with remote tracking where remote no longer exists)
python -m git_garden --delete

# see usage/syntax help
python -m git_garden --help
```

## Pre-PR Checks

```
# Ruff (r/w)
ruff format .
ruff check . --fix

# Pytest
pytest --cov git_garden --cov-report xml:cov.xml --cov-report term

# Linting
tox

# Generate Documentation
sphinx-build -b html . docs
docs\index.html

# Compilation (pyd is imported / run as normal)
mypyc git_garden\__init__.py
python ..\__main__.py --remote --ff --delete
```
