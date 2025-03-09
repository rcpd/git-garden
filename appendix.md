# Appendix

Miscellaneous information / project resources.

## Develop Installation

```
python -m pip install -e . # pip, or;
uv sync --extra dev --frozen # uv (see [appendix.md](./appendix.md))
```

## Pre-PR Checks

```pwsh
# functional testing
python -m git_garden --remote --ff --delete

# run all the checks like the pipeline would (with whatever version of Python is installed on the pipeline image)
# first run can be a little slow creating venv(s) or if dependencies have changed but they will be cached/reused after that
tox -e fix # attempt to fix any violations (this will reformat your code!)
tox -e pr # run the same checks as the pipeline

# generate documentation (main project only)
sphinx-build -b html . docs
docs\index.html
```

## Installing uv

Mini-guide for installing/configuring `uv`:

```pwsh
# install
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" 

# terminal/VSC needs a restart after setting persistent env var before they will take effect
[System.Environment]::SetEnvironmentVariable("Path","$env:USERPROFILE\.local\bin;$env:Path","User") # add to path
[System.Environment]::SetEnvironmentVariable("UV_PROJECT_ENVIRONMENT","venv","User")
$cache = python -m pip cache dir # share cache with pip
[System.Environment]::SetEnvironmentVariable("UV_CACHE_DIR",$cache,"User")
[System.Environment]::SetEnvironmentVariable("UV_LINK_MODE","copy","User") # if cache and venv on seperate drives
```

Example usage (experimental):

```pwsh
# install python (if needed)
uv python list
uv python install cpython-3.13.2-windows-x86_64-none
uv python pin cpython-3.13.2-windows-x86_64-none

# other useful features: https://docs.astral.sh/uv/reference/cli/
uv venv venv; venv\scripts\activate
uv pip list

# `sync` will always do an editable install of the base project
# but `optional-dependencies` require `--extra <group>` or `--all-extras`
# `sync` will also implicitly `lock` without `--frozen`
uv sync --extra dev --frozen

# if falling back to pip
uv pip install pip
```