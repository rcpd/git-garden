import pytest
import logging
import os
import sys
import runpy
import shutil
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
        quiet=True,
        no_fetch=True,
        no_prune=True,
        include=["git-garden"],
        exclude=["foobar"],
        remote=True,
        purge=True,
        ff=True,
        delete=True,
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


@pytest.fixture(scope="session")
def root_branch() -> Generator[str, None, None]:
    """
    Yield the root branch.

    :yield: Name of the root branch for test project.
    """
    yield "main"


def test_parse_branches(gg: GitGarden) -> None:
    """
    Test "git branch" parsing.

    :param gg: GitGarden instance.
    """
    unformatted_local = "* foobar\n  main\n".encode()
    formatted_local = "'foobar origin/foobar '\n'main origin/main '\n".encode()
    unformatted_remote = "  origin/foobar\n  origin/main\n".encode()
    formatted_remote = "'origin/foobar  '\n'origin/main  '\n".encode()

    assert gg.parse_branches(unformatted_local) == ["foobar", "main"]
    assert gg.parse_branches(formatted_local, upstream=True) == [
        "foobar origin/foobar",
        "main origin/main",
    ]
    assert gg.parse_branches(unformatted_remote) == ["origin/foobar", "origin/main"]
    assert gg.parse_branches(formatted_remote, upstream=True) == [
        "origin/foobar",
        "origin/main",
    ]


def test_get_dirs_with_depth(logger: logging.Logger, args: Namespace, dir: str) -> None:
    """
    Test the .git search algorithm.
    Create an empty repo and delete it afterwards.

    :param gg: GitGarden instance.
    """
    # create GG instance with custom args
    gg = GitGarden(logger, args)
    gg.args.include = ["tmp"]
    gg.args.exclude = []

    # create a fake test repo
    repo = os.path.join(dir, "tmp")
    git = os.path.join(repo, ".git")
    os.makedirs(git, exist_ok=True)

    # attest the function & clean up the test repo
    try:
        result = gg.get_dirs_with_depth(repo)
        assert result[0] == repo
    finally:
        shutil.rmtree(repo)


def test_check_git_status(gg: GitGarden, dir: str) -> None:
    """
    Inject a change into the working tree and check that the status is dirty.
    Revert the change before attesting the state.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    # "touch" a file to dirty the working tree
    tmp_file = "test.tmp"
    with open(tmp_file, "w") as f:
        f.write("")

    # attest the working tree state & clean up test file
    status = gg.check_git_status(dir=dir)
    try:
        assert status is True
    finally:
        os.remove(tmp_file)


def test_branch_crud(gg: GitGarden, dir: str) -> None:
    """
    Test the creation and deletion of a branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    # create local branch
    branch = "test-branch"
    gg.create_branch(branch, dir=dir)

    try:
        # attest local only status of test branch
        assert branch in gg.list_local_branches(dir=dir)
        assert f"{branch} origin/{branch}" not in gg.list_local_branches(
            dir=dir, upstream=True
        )

        # push test branch & attest the status of the remote
        gg.push_branch(branch, dir=dir)
        assert f"origin/{branch}" in gg.list_remote_branches(dir=dir)
    finally:
        # cleanup test branches
        gg.delete_branch(branch, dir=dir)
        gg.delete_branch(branch, branch_type="remote", dir=dir)
        gg.delete_branch(branch, branch_type="tracking", dir=dir)

    # attest branch deletion
    assert branch not in gg.list_local_branches(dir=dir)
    assert branch not in gg.list_remote_branches(dir=dir)


def test_list_branches(gg: GitGarden, dir: str) -> None:
    """
    Test the listing of branches.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    # create the test branch on local & remote
    branch = "'quote-branch'"
    gg.create_branch(branch, dir=dir)
    gg.push_branch(branch)

    try:
        # attest the state of the branch in local & remote
        assert branch in gg.list_local_branches(dir=dir)
        assert f"{branch} origin/{branch}" in gg.list_local_branches(
            dir=dir, upstream=True
        )
        assert f"origin/{branch}" in gg.list_remote_branches(dir=dir)
        assert f"origin/{branch}" in gg.list_remote_branches(dir=dir, upstream=True)
    finally:
        # cleanup the test branch
        gg.delete_branch(branch)


def test_find_root_branch(gg: GitGarden, dir: str) -> None:
    """
    Test identification of the root branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    assert (
        gg.find_root_branch(gg.list_local_branches(dir), gg.list_remote_branches(dir))
        == "main"
    )


def test_fetch_and_purge(gg: GitGarden, dir: str) -> None:
    """
    Test purging of the remote tracking branches & fetching of the remote.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    # purge remote tracking branches
    gg.purge_tracking_branches(dir=dir)

    try:
        assert gg.list_remote_branches(dir=dir) == []
    finally:
        # fetch remote (restoring the tracking branches)
        gg.fetch(dir, prune=False)

    assert "main" in gg.list_local_branches(dir=dir)
    assert "origin/main" in gg.list_remote_branches(dir=dir)


def test_branch_ahead(gg: GitGarden, dir: str) -> None:
    """
    Test the "ahead" status of a branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    # skip tests that require branch switching if working tree is dirty
    if gg.check_git_status():
        pytest.skip(
            "test_branch_ahead: Test cannot be run while working tree is dirty."
        )

    # create a test branch in the "ahead" state
    test_branch = "gitgarden-test-branch-ahead"
    original_branch = gg.find_current_branch(dir=dir)
    gg.create_branch(test_branch, root_branch=original_branch, dir=dir)
    gg.push_branch(test_branch, dir=dir)  # instantiate remote
    gg.switch_branch(test_branch, dir=dir)
    gg.create_commit("test commit", dir=dir)  # local branch is now ahead

    # attest that the test branch is ahead
    branches = gg.list_local_branches(dir=dir, upstream=True)
    try:
        for branch in branches:
            if branch.startswith(test_branch):
                assert "[ahead" in branch
    finally:
        # restore original branch & cleanup test branch
        gg.switch_branch(original_branch, dir=dir)
        gg.delete_branch(test_branch, dir=dir)
        gg.delete_branch(test_branch, branch_type="remote", dir=dir)
        gg.delete_branch(test_branch, branch_type="tracking", dir=dir)


def test_branch_behind_and_ff(gg: GitGarden, dir: str, root_branch: str) -> None:
    """
    Test the "behind" status of a branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    # skip tests that require branch switching if working tree is dirty
    if gg.check_git_status():
        pytest.skip(
            "test_branch_behind: Test cannot be run while working tree is dirty."
        )

    # create a test branch that is "behind" the remote
    test_branch = "gitgarden-test-branch-behind-and-ff"
    original_branch = gg.find_current_branch(dir=dir)
    gg.create_branch(test_branch, root_branch=original_branch, dir=dir)
    gg.switch_branch(test_branch, dir=dir)
    gg.create_commit("test commit", dir=dir)
    gg.push_branch(
        test_branch, dir=dir, force=True
    )  # instantiate remote with +1 commit
    gg.delete_commit(dir=dir)  # local branch is now behind

    try:
        # attest the test branch is behind
        branches = gg.list_local_branches(dir=dir, upstream=True)
        for branch in branches:
            if branch.startswith(test_branch):
                assert "[behind" in branch

        # attest the test branch is up to date
        gg.switch_branch(original_branch, dir=dir)
        gg.fast_forward_branch(test_branch, root_branch, dir=dir)

        # attest the test branch is behind
        branches = gg.list_local_branches(dir=dir, upstream=True)
        for branch in branches:
            if branch.startswith(test_branch):
                assert "[behind" not in branch

    finally:
        # restore original branch & cleanup test branch
        gg.delete_branch(test_branch, dir=dir)
        gg.delete_branch(test_branch, branch_type="remote", dir=dir)
        gg.delete_branch(test_branch, branch_type="tracking", dir=dir)


def test_branch_gone(gg: GitGarden, dir: str) -> None:
    """
    Test the "gone" status of a branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    # create and orphan a test branch
    test_branch = "gitgarden-test-branch-gone"
    gg.create_branch(test_branch, dir=dir)
    gg.push_branch(test_branch, dir=dir)
    gg.delete_branch(test_branch, dir=dir, branch_type="remote")

    # attest the test branch is orphaned
    branches = gg.list_local_branches(dir=dir, upstream=True)
    try:
        for branch in branches:
            if branch.startswith(test_branch):
                assert branch.endswith("[gone]")
    finally:
        # cleanup the test branches
        gg.delete_branch(test_branch, dir=dir, branch_type="local")
        gg.delete_branch(test_branch, dir=dir, branch_type="tracking")


def test_branch_remote_only(gg: GitGarden, dir: str) -> None:
    """
    Test the "remote" status of a branch.

    :param gg: GitGarden instance.
    :param dir: Path to the git-garden directory.
    """
    # create a test branch that only exists on the remote
    test_branch = "gitgarden-test-branch-remote-only"
    gg.create_branch(test_branch, dir=dir)
    gg.push_branch(test_branch, dir=dir)
    gg.delete_branch(test_branch, dir=dir, branch_type="local")

    # attest the test branch only exists on the remote
    try:
        assert gg.check_branch_remote_only(
            "origin/" + test_branch,
            gg.list_local_branches(dir),
            gg.list_remote_branches(dir),
        )
    finally:
        # cleanup test branches
        gg.delete_branch(test_branch, dir=dir, branch_type="remote")
        gg.delete_branch(test_branch, dir=dir, branch_type="tracking")


def test_git_garden_module() -> None:
    """
    Test module execution (dry run).
    """
    # patch sys.argv with git-garden cli params for dry run
    original_argv = sys.argv

    try:
        sys.argv = [
            sys.argv[0],
            "--directory",
            ".",
            "--quiet",
            "--no-fetch",
            "--no-prune",
        ]

        # mimic -m execution
        runpy.run_module("git_garden", run_name="__main__", alter_sys=True)
    finally:
        # restore sys.argv
        sys.argv = original_argv
