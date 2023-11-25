import pytest
import logging
import os

from git_garden import GitGarden
from argparse import Namespace


@pytest.fixture(scope="session", autouse=True)
def logger():
    logger = logging.getLogger(os.path.basename(__file__))
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    yield logger
    logging.shutdown()


@pytest.fixture(scope="session", autouse=True)
def args():
    """
    Mimic the creation of the argparse.Namespace object with defaults.
    """
    return Namespace(
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


def test_branch_crud():
    branch = "test-branch"
    assert GitGarden._create_branch(branch).returncode == 0
    assert GitGarden._delete_branch(branch).returncode == 0


def test_git_garden(logger: logging.Logger, args: Namespace):
    """
    Test git_garden.

    :param logger: Logger to use for output.
    :param args: Command line arguments.
    """
    # if GitGarden._check_git_status():
    #     pytest.skip("Test cannot be run while working tree is dirty.")

    assert GitGarden(logger, args) is not None
