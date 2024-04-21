import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 10):
    install_requires = ["typing-extensions"]
else:
    install_requires = []

setup(
    name="git-garden",
    version="0.2.3",
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        "dev": [
            "ruff",
            "sphinx",
            "sphinx-autodoc-typehints",
            "tox",
            "pytest",
            "pytest-cov",
            "pydoclint",
            "mypy",
        ]
    },
)
