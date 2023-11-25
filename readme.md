# Git-Garden

## Installation

```
# no external dependencies other than git itself
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
python garden.py --directory D:\dev

# attempt to fast-forward main/master if behind
python garden.py --ff

# include or exclude directories matching a sub-string
# i.e. for D:\dev\MyProject & D:\dev\MyOtherProject
python garden.py --include MyProject --include MyOtherProject
python garden.py --exclude MyProject --exclude MyOtherProject

# skip reporting basic current/ahead/behind status
python garden.py --quiet

# attempt to delete orphaned local branches
# (branches with remote tracking where remote no longer exists)
python garden.py --delete

# see usage/syntax help
python garden.py --help
```

## Test Cases (Non-Exhaustive)

```
python garden.py
python garden.py --no-fetch --no-prune --remote
python garden.py --no-fetch --no-prune --ff --delete --quiet

git switch -c temp # local only
git switch -c temp2; git push -f; git push origin --delete temp2 # gone
git switch -c temp3; git commit -m "Temp" --allow-empty; git push -f; git reset HEAD~ --hard # behind
git switch -c temp4; git push -f; git push origin --delete temp4; git reset HEAD~ --soft # uncommitted changes

git switch git-garden -f; git branch -D temp temp2 temp3 temp4 # cleanup
git push origin --delete temp temp2 temp3 temp4 # cleanup
```

## Pre-PR Checks

```
# ruff (r/w)
ruff format .
ruff check . --fix

# tests + ruff (r/o)
tox

# Generate Documentation
sphinx-build -b html . docs
```
