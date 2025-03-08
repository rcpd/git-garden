# Git-Garden

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

## Pre-PR Checks

```pwsh
# functional testing
python -m git_garden --remote --ff --delete

# run all the checks like the pipeline would (with whatever version of Python is installed on the pipeline image)
# first run can be a little slow creating venv(s) or if dependencies have changed but they will be cached/reused after that
tox -e pr # run the same checks as the pipeline
tox -e fix # attempt to fix any violations (this will reformat your code!)

# generate documentation (main project only)
sphinx-build -b html . docs
docs\index.html

# compilation (pyd is imported / run as normal)
mypyc git_garden\__init__.py
python ..\__main__.py --remote --ff --delete
```