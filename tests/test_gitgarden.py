import pytest
import logging
import os
import sys
import runpy
import shutil
from git_garden import GitGarden
from argparse import Namespace
from typing import Generator
import uuid


@pytest.fixture(scope="session")
def logger() -> Generator[logging.Logger, None, None]:
    """
    Setup the test logger.
    """
    logger = logging.getLogger(os.path.basename(__file__))
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    yield logger
    logging.shutdown()


@pytest.fixture(scope="session")
def args() -> Generator[Namespace, None, None]:
    """
    Mimic the creation of the argparse.Namespace object.
    Note: these are a modified version of the defaults.
    """
    yield Namespace(
        dir=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        depth=3,
        no_fetch=True,
        no_prune=False,
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
    """
    yield GitGarden(logger, args)


@pytest.fixture(scope="session")
def dir(gg: GitGarden) -> Generator[str, None, None]:
    """
    Path to the git-garden directory.
    """
    yield os.path.join(gg.args.dir, "git-garden")


@pytest.fixture(scope="session")
def root_branch() -> Generator[str, None, None]:
    """
    Yield the root branch.
    """
    yield "main"


@pytest.fixture(scope="session")
def guid(length: int = 8) -> Generator[str, None, None]:
    """
    Generate a short GUID of the specified length.
    """
    return str(uuid.uuid4()).replace("-", "")[:length]


def touch(tmp_file: str = "test.tmp") -> None:
    """
    "touch" a file to dirty the working tree.
    """
    with open(tmp_file, "w") as f:
        f.write("")


def test_parse_branches(gg: GitGarden) -> None:
    """
    Test "git branch" parsing.
    """
    unformatted_local = "* foobar\n  main\n"
    formatted_local = "'foobar origin/foobar '\n'main origin/main '\n"
    unformatted_remote = "  origin/foobar\n  origin/main\n"
    formatted_remote = "'origin/foobar  '\n'origin/main  '\n"

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


def test_get_dirs_with_depth(logger: logging.Logger, args: Namespace, dir: str, guid: str) -> None:
    """
    Test the .git search algorithm.
    Create an empty repo and delete it afterwards.
    """
    # create GG instance with custom args
    gg = GitGarden(logger, args)
    tmp_inc = f"tmp_inc_{guid}"
    tmp_exc = f"tmp_exc_{guid}"
    gg.args.include = [tmp_inc]
    gg.args.exclude = [tmp_exc]

    # create fake test repos
    base_dir = os.path.join(dir, f"tmp_{guid}")
    inc_repo = os.path.join(base_dir, "mid", tmp_inc)
    exc_repo = os.path.join(base_dir, "mid", tmp_exc)
    inc_git = os.path.join(inc_repo, ".git")
    exc_git = os.path.join(exc_repo, ".git")
    os.makedirs(inc_git, exist_ok=True)
    os.makedirs(exc_git, exist_ok=True)

    # attest test cases & clean up the test repo
    try:
        # depth=0
        assert gg.get_dirs_with_depth(base_dir, depth=0) == []

        # multi-level search
        result = gg.get_dirs_with_depth(base_dir)
        assert inc_repo in result
        assert exc_repo not in result

        # search terminated by non-include git repo
        mid_git = os.path.join(base_dir, "mid", ".git")
        os.makedirs(mid_git, exist_ok=True)
        assert gg.get_dirs_with_depth(base_dir) == []
    finally:
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)


def test_check_git_status(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Inject a change into the working tree and check that the status is dirty.
    Revert the change after attesting the state.
    """
    base_dir = os.path.join(dir, f"tmp_{guid}")
    os.makedirs(base_dir, exist_ok=True)
    tmp_file = f"{guid}.tmp"
    touch(tmp_file)  # can overwrite existing

    try:
        # attest the working tree state & clean up test file
        assert gg.check_git_status(dir=dir) is True
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)


def test_branch_crud(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Test the creation and deletion of a branch.
    """
    # create local branch
    branch = f"test-branch-{guid}"
    gg.create_branch(branch, dir=dir)

    try:
        # attest local only status of test branch
        assert branch in gg.list_local_branches(dir=dir)
        assert f"{branch} origin/{branch}" not in gg.list_local_branches(dir=dir, upstream=True)

        # push test branch & attest the status of the remote
        gg.push_branch(branch, dir=dir)
        assert f"origin/{branch}" in gg.list_remote_branches(dir=dir)
    finally:
        # cleanup test branches
        gg.delete_branch(branch, branch_type="all", dir=dir)

    # attest branch deletion
    assert branch not in gg.list_local_branches(dir=dir)
    assert branch not in gg.list_remote_branches(dir=dir)

    # test error handling of non-existent branch type
    with pytest.raises(ValueError):
        gg.delete_branch(branch, branch_type="foobar", dir=dir)


def test_list_branches(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Test the listing of branches.
    """
    # create the test branch on local & remote
    branch = f"'gitgarden-test-quote-branch-{guid}'"
    gg.create_branch(branch, dir=dir)
    gg.push_branch(branch, dir=dir)

    try:
        # attest the state of the branch in local & remote
        assert branch in gg.list_local_branches(dir=dir)
        assert f"{branch} origin/{branch}" in gg.list_local_branches(dir=dir, upstream=True)
        assert f"origin/{branch}" in gg.list_remote_branches(dir=dir)
        assert f"origin/{branch}" in gg.list_remote_branches(dir=dir, upstream=True)
    finally:
        # cleanup the test branch
        gg.delete_branch(branch, branch_type="all", dir=dir)


def test_find_root_branch(gg: GitGarden, dir: str) -> None:
    """
    Test identification of the root branch.
    """
    assert gg.find_root_branch(gg.list_local_branches(dir), gg.list_remote_branches(dir)) == "main"
    assert gg.find_root_branch([], []) == ""


def test_find_custom_root_branch(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Test identification of a custom (--root) root branch.
    """
    branch = f"production-{guid}"
    gg.args.root = [branch]
    gg.create_branch(branch, dir=dir)

    try:
        assert gg.find_root_branch(gg.list_local_branches(dir), []) == branch
    finally:
        # cleanup the test branch
        gg.delete_branch(branch, branch_type="all", dir=dir)


def test_fetch_and_purge(gg: GitGarden, dir: str) -> None:
    """
    Test purging of the remote tracking branches & fetching of the remote.
    """
    # purge remote tracking branches
    gg.purge_tracking_branches(dir=dir)

    try:
        assert gg.list_remote_branches(dir=dir) == []
    finally:
        # fetch remote (restoring the tracking branches)
        gg.fetch(dir, prune=False)
        gg.fetch(dir, prune=True)

    assert "main" in gg.list_local_branches(dir=dir)
    assert "origin/main" in gg.list_remote_branches(dir=dir)


def test_switch_branch(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Test branch switching.
    """
    # skip tests that require branch switching if working tree is dirty
    if gg.check_git_status(dir):
        pytest.skip("test_branch_ahead: Test cannot be run while working tree is dirty.")

    # test success case
    test_branch = f"gitgarden-test-branch-{guid}"
    original_branch = gg.find_current_branch(dir=dir)
    gg.create_branch(test_branch, root_branch=original_branch, dir=dir)

    try:
        gg.switch_branch(test_branch, dir=dir)
        assert gg.find_current_branch(dir=dir) == test_branch
    finally:
        gg.switch_branch(original_branch, dir=dir)
        gg.delete_branch(test_branch, dir=dir)

    # test failure case
    tmp_file = f"{guid}.tmp"
    touch(tmp_file)
    try:
        assert gg.switch_branch("foobar", dir) is None
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)


def test_branch_ahead(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Test the "ahead" status of a branch.
    """
    # skip tests that require branch switching if working tree is dirty
    if gg.check_git_status(dir):
        pytest.skip("test_branch_ahead: Test cannot be run while working tree is dirty.")

    # create a test branch in the "ahead" state
    test_branch = f"gitgarden-test-branch-ahead-{guid}"
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
        gg.delete_branch(test_branch, branch_type="all", dir=dir)


def test_branch_behind_and_ff(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Test the "behind" status of a branch.
    """
    # skip tests that require branch switching if working tree is dirty
    if gg.check_git_status(dir):
        pytest.skip("test_branch_behind: Test cannot be run while working tree is dirty.")

    # create a test branch that is "behind" the remote
    test_branch = f"gitgarden-test-branch-behind-and-ff-{guid}"
    original_branch = gg.find_current_branch(dir=dir)
    gg.create_branch(test_branch, root_branch=original_branch, dir=dir)
    gg.switch_branch(test_branch, dir=dir)
    gg.create_commit("test commit", dir=dir)
    gg.push_branch(test_branch, dir=dir, force=True)  # instantiate remote with +1 commit
    gg.delete_commit(dir=dir)  # local branch is now behind

    try:
        # attest the test branch is behind
        branches = gg.list_local_branches(dir=dir, upstream=True)
        for branch in branches:
            if branch.startswith(test_branch):
                assert "[behind" in branch

        # attest the test branch is up to date
        gg.fast_forward_branch(dir=dir)
        branches = gg.list_local_branches(dir=dir, upstream=True)
        for branch in branches:
            if branch.startswith(test_branch):
                assert "[behind" not in branch

    finally:
        # restore original branch & cleanup test branch
        gg.switch_branch(original_branch, dir=dir)
        gg.delete_branch(test_branch, branch_type="all", dir=dir)


def test_branch_behind_and_ff_all(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Test pulling a non-current branch.
    """
    # skip tests that require branch switching if working tree is dirty
    if gg.check_git_status(dir):
        pytest.skip("test_branch_behind: Test cannot be run while working tree is dirty.")

    # create a test branch that is "behind" the remote
    test_branch = f"gitgarden-test-branch-behind-and-ff-all-{guid}"
    original_branch = gg.find_current_branch(dir=dir)
    gg.create_branch(test_branch, root_branch=original_branch, dir=dir)
    gg.switch_branch(test_branch, dir=dir)
    gg.create_commit("test commit", dir=dir)
    gg.push_branch(test_branch, dir=dir, force=True)  # instantiate remote with +1 commit
    gg.delete_commit(dir=dir)  # local branch is now behind

    try:
        # switch back to original branch and pull the test branch
        gg.switch_branch(original_branch, dir=dir)
        gg.pull_non_current_branch(test_branch, dir=dir)

        # attest the test branch is up to date
        branches = gg.list_local_branches(dir=dir, upstream=True)
        for branch in branches:
            if branch.startswith(test_branch):
                assert "[behind" not in branch

    finally:
        # cleanup test branch
        gg.delete_branch(test_branch, branch_type="all", dir=dir)


def test_branch_gone(gg: GitGarden, dir: str, guid: str) -> None:
    """
    Test the "gone" status of a branch.
    """
    # create and orphan a test branch
    test_branch = f"gitgarden-test-branch-gone-{guid}"
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


def test_branch_remote_only(gg: GitGarden, dir: str, root_branch: str, guid: str) -> None:
    """
    Test the "remote" status of a branch.
    """
    # create a test branch that only exists on the remote
    test_branch = f"gitgarden-test-branch-remote-only-{guid}"
    gg.create_branch(test_branch, dir=dir)
    gg.push_branch(test_branch, dir=dir)
    gg.delete_branch(test_branch, dir=dir, branch_type="local")

    # attest the test branch only exists on the remote
    try:
        local_branches = gg.list_local_branches(dir)
        remote_branches = gg.list_remote_branches(dir)
        assert gg.check_branch_remote_only(
            "origin/" + test_branch,
            local_branches,
            remote_branches,
        )
        assert not gg.check_branch_remote_only(root_branch, local_branches, remote_branches)
    finally:
        # cleanup test branches
        gg.delete_branch(test_branch, dir=dir, branch_type="remote")
        gg.delete_branch(test_branch, dir=dir, branch_type="tracking")


def test_git_garden_module() -> None:
    """
    Test module execution (dry run).

    dir=".",
    depth=3,
    no_fetch=True,
    no_prune=False,
    include=[],
    exclude=[],
    remote=False,
    purge=False,
    ff=False,
    ff_all=False
    delete=False
    root=["main","master"]
    """
    # patch sys.argv with git-garden cli params for dry run
    original_argv = sys.argv

    try:
        sys.argv = [
            sys.argv[0],
            "--dir",
            ".",
            "--no-fetch",
        ]

        # mimic -m execution
        runpy.run_module("git_garden", run_name="__main__", alter_sys=True)
    finally:
        # restore sys.argv
        sys.argv = original_argv


def test_git_garden_main(logger: logging.Logger, args: Namespace, dir: str) -> None:
    """
    Test main() execution.
    """
    gg = GitGarden(logger, args)

    # inverse the default/module run arguments for additional coverage
    gg.args.dir = (".",)
    gg.args.depth = (3,)
    gg.args.no_fetch = False
    gg.args.no_prune = True
    gg.args.include = []
    gg.args.exclude = []
    gg.args.remote = True
    gg.args.purge = True
    gg.args.ff = True
    gg.args.ff_all = True
    gg.args.delete = True
    gg.args.root = ["production"]
    gg.main([dir])

    with pytest.raises(RuntimeError):
        gg = GitGarden(logger, args, git="foobar")
        gg.main([dir])
