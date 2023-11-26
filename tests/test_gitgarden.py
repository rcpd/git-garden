import pytest
import logging
import os
import shutil

from git_garden import GitGarden
from argparse import Namespace
from typing import Generator


@pytest.fixture(scope="session")
def logger() -> Generator[logging.Logger]:
    """
    Setup the test logger.

    :yield: Logger instance.
    """
    logger = logging.getLogger(os.path.basename(__file__))
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    yield logger
    logging.shutdown()


@pytest.fixture(scope="session")
def args() -> Generator[Namespace]:
    """
    Mimic the creation of the argparse.Namespace object with defaults.

    :yields: Namespace object with pre-defined defaults.
    """
    yield Namespace(
        directory=r"D:\dev",
        depth=3,
        quiet=False,
        no_fetch=False,
        no_prune=False,
        include=["git-garden"],
        exclude=[],
        remote=False,
        purge=False,
        ff=False,
        delete=False,
    )


def test_git_status() -> None:
    """
    Inject a change into the working tree and check that the status is dirty.
    Revert the change before attesting the state.
    """
    tmp_file = "test.tmp"
    shutil.touch(tmp_file)
    status = GitGarden._check_git_status()
    os.remove(tmp_file)
    assert status is True


def test_branch_crud() -> None:
    """
    Test the creation and deletion of a branch.
    """
    branch = "test-branch"
    assert GitGarden._create_branch(branch).returncode == 0
    assert GitGarden._delete_branch(branch).returncode == 0


def test_git_garden_purge(logger: logging.Logger, args: Namespace) -> None:
    """
    Run GitGarden with --purge

    :param logger: Logger to use for output.
    :param args: Command line arguments.
    """
    args.purge = True
    GitGarden(logger, args)


def test_git_garden(logger: logging.Logger, args: Namespace) -> None:
    """
    Run GitGarden with default arguments (limited to GitGarden repo).

    :param logger: Logger to use for output.
    :param args: Command line arguments.
    """
    # if GitGarden._check_git_status():
    #     pytest.skip("Test cannot be run while working tree is dirty.")

    GitGarden(logger, args)
