import sys
from setuptools import setup, find_packages

dev_base = [
    "ruff",
    "sphinx",
    "sphinx-autodoc-typehints",
    "tox",
    "pytest",
    "pytest-cov",
    "mypy",
]

if sys.version_info >= (3, 8):
    dev_dependencies = dev_base + ["pydoclint"]
else:
    dev_dependencies = dev_base

if sys.version_info < (3, 10):
    install_requires = ["typing-extensions"]
else:
    install_requires = []

setup(
    name="git-garden",
    version="0.3.1",
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={"dev": dev_dependencies},
)
