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

## Test Cases (Non-Exhaustive)

```
python -m git_garden
python -m git_garden --no-fetch --no-prune --remote
python -m git_garden --no-fetch --no-prune --ff --delete --quiet

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

# linting + tests (r/o)
tox

# Generate Documentation
sphinx-build -b html . docs
```
