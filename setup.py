import sys
from setuptools import setup, find_packages

install_requires = []
dev_dependencies = [
    "ruff",
    "sphinx",
    "sphinx-autodoc-typehints",
    "tox",
    "pytest",
    "pytest-cov",
    "mypy",
]

if sys.version_info >= (3, 8):
    dev_dependencies.append("pydoclint")

if sys.version_info < (3, 10):
    install_requires.append("typing-extensions")

setup(
    name="git-garden",
    version="0.3.1",
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={"dev": dev_dependencies},
)
