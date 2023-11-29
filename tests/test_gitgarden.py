import pytest
import logging
import os

from git_garden import GitGarden
from argparse import Namespace
from typing import Generator

# TODO: get_dirs_with_depth


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


@pytest.fixture(scope="session")
def dir(gg: GitGarden) -> Generator[str, None, None]:
    """
    Path to the git-garden directory.

    :param gg: GitGarden instance.
    :yield: Path to the git-garden directory.
    """
    yield os.path.join(gg.args.directory, "git-garden")


def test_git_status(gg: GitGarden, dir: str) -> None:
    """
    Inject a change into the working tree and check that the status is dirty.
    Revert the change before attesting the state.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    tmp_file = "test.tmp"
    with open(tmp_file, "w") as f:
        f.write("")
    status = gg.check_git_status(dir=dir)
    os.remove(tmp_file)
    assert status is True


def test_branch_crud(gg: GitGarden, dir: str) -> None:
    """
    Test the creation and deletion of a branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    branch = "test-branch"
    gg.delete_branch(branch, dir=dir) # preemptively delete branch if it exists

    gg.create_branch(branch, dir=dir)
    gg.push_branch(branch, dir=dir)

    assert branch in gg.list_local_branches(dir=dir)
    assert f"origin/{branch}" in gg.list_remote_branches(dir=dir)

    gg.delete_branch(branch, dir=dir)
    gg.delete_branch(branch, remote=True, dir=dir)
    gg.fetch(prune=True, dir=dir)

    assert branch not in gg.list_local_branches(dir=dir)
    assert branch not in gg.list_remote_branches(dir=dir)


def test_list_branches(gg: GitGarden, dir: str) -> None:
    """
    Test the listing of branches.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    gg.create_branch("'quote-branch'")

    assert "main" in gg.list_local_branches(dir=dir)
    assert "main origin/main" in gg.list_local_branches(dir=dir, upstream=True)
    assert "origin/main" in gg.list_remote_branches(dir=dir)
    assert "'quote-branch'" in gg.list_local_branches(dir=dir)

    gg.delete_branch("'quote-branch'")


def test_find_root_branch(gg: GitGarden, dir: str) -> None:
    """
    Test the finding of the root branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    assert (
        gg.find_root_branch(gg.list_local_branches(dir), gg.list_remote_branches(dir))
        == "main"
    )


def test_fetch_and_purge(gg: GitGarden, dir: str) -> None:
    """
    Run GitGarden with --purge.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    gg.purge_remote_branches(dir=dir)
    assert gg.list_remote_branches(dir=dir) == []

    gg.fetch(dir)  # restore remote branches
    assert "main" in gg.list_local_branches(dir=dir)
    assert "origin/main" in gg.list_remote_branches(dir=dir)


def test_branch_ahead(gg: GitGarden, dir: str) -> None:
    """
    Test the "ahead" status of a branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    if gg.check_git_status():
        pytest.skip("Test cannot be run while working tree is dirty.")

    test_branch = "gitgarden-test-branch-ahead"
    original_branch = gg.find_current_branch(dir=dir)
    
    gg.delete_branch(test_branch, dir=dir) # preemptively delete branch if it exists
    gg.create_branch(test_branch, root_branch="main", dir=dir)
    gg.push_branch(test_branch, force=True, dir=dir)  # instantiate remote

    gg.switch_branch(test_branch, dir=dir)
    gg.create_commit("test commit", dir=dir)  # local branch is now ahead
    
    if gg.check_git_status():
        raise RuntimeError("Working tree was not dirty at the beginning of the test but is now)")
    gg.switch_branch(original_branch, dir=dir)

    branches = gg.list_local_branches(dir=dir, upstream=True)
    for branch in branches:
        if branch.startswith(test_branch):
            assert "[ahead" in branch

    gg.delete_branch(test_branch, dir=dir)


def test_branch_behind(gg: GitGarden, dir: str) -> None:
    """
    Test the "behind" status of a branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    if gg.check_git_status():
        pytest.skip("Test cannot be run while working tree is dirty.")

    test_branch = "gitgarden-test-branch-behind"
    original_branch = gg.find_current_branch(dir=dir)
    
    gg.delete_branch(test_branch, dir=dir) # preemptively delete branch if it exists
    gg.create_branch(test_branch, root_branch="main", dir=dir)
    
    gg.switch_branch(test_branch, dir=dir)
    gg.create_commit("test commit", dir=dir)
    gg.push_branch(test_branch, force=True, dir=dir)  # instantiate remote with +1 commit
    gg.delete_commit(dir=dir)  # local branch is now behind

    if gg.check_git_status():
        raise RuntimeError("Working tree was not dirty at the beginning of the test but is now)")
    gg.switch_branch(original_branch, dir=dir)

    branches = gg.list_local_branches(dir=dir, upstream=True)
    for branch in branches:
        if branch.startswith(test_branch):
            assert "[behind" in branch

    gg.delete_branch(test_branch, dir=dir)
    gg.delete_branch


def test_git_garden(gg: GitGarden) -> None:
    """
    Run GitGarden with default arguments (except limited to GitGarden repo).

    :param gg: GitGarden instance.
    """
    gg.main(gg.get_dirs_with_depth(gg.args.directory, depth=gg.args.depth))
