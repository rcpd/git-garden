from setuptools import setup, find_packages

setup(
    name="git-garden",
    version="0.2",
    packages=find_packages(),
    install_requires=[],
    extras_require={
        "dev": [
            "ruff",
            "sphinx",
            "sphinx-autodoc-typehints",
            "tox",
            "pytest",
            "pytest-cov",
        ]
    },
)
