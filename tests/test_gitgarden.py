import pytest
import logging
import os

from git_garden import GitGarden
from argparse import Namespace
from typing import Generator


@pytest.fixture(scope="session")
def logger() -> Generator[logging.Logger, None, None]:
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
def args() -> Generator[Namespace, None, None]:
    """
    Mimic the creation of the argparse.Namespace object with defaults.

    :yields: Namespace object with pre-defined defaults.
    """
    yield Namespace(
        directory=os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ),
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


@pytest.fixture(scope="session")
def gg(logger: logging.Logger, args: Namespace) -> Generator[GitGarden, None, None]:
    """
    Setup the default GitGarden instance the same way __main__.py does.

    :param logger: Logger instance.
    :param args: Namespace object with pre-defined defaults.
    :yield: GitGarden instance.
    """
    yield GitGarden(logger, args)


def test_git_status(gg: GitGarden) -> None:
    """
    Inject a change into the working tree and check that the status is dirty.
    Revert the change before attesting the state.

    :param gg: GitGarden instance.
    """
    tmp_file = "test.tmp"
    with open(tmp_file, "w") as f:
        f.write("")
    status = gg.check_git_status()
    os.remove(tmp_file)
    assert status is True


def test_branch_crud(gg: GitGarden) -> None:
    """
    Test the creation and deletion of a branch.

    :param gg: GitGarden instance.
    """
    branch = "test-branch"
    assert gg.create_branch(branch).returncode == 0
    assert gg.delete_branch(branch).returncode == 0


def test_fetch_and_purge(gg: GitGarden) -> None:
    """
    Run GitGarden with --purge.

    :param gg: GitGarden instance.
    """
    dir = os.path.join(gg.args.directory, "git-garden")
    gg.purge_remote_branches(dir)
    assert gg.list_remote_branches(dir) == [""]  # FIXME

    gg.fetch(dir)
    assert len(gg.list_remote_branches(dir)) > 1  # FIXME
    assert "main" in gg.list_local_branches(dir)  # FIXME: upstream vs not


def test_git_garden(gg: GitGarden) -> None:
    """
    Run GitGarden with default arguments (except limited to GitGarden repo).

    :param gg: GitGarden instance.
    """
    # if GitGarden._check_git_status():
    #     pytest.skip("Test cannot be run while working tree is dirty.")
    gg.main(gg.get_dirs_with_depth(gg.args.directory, gg.args.depth))
