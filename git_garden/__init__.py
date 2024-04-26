import os
import logging
import subprocess
import shutil
import argparse
import sys

if sys.version_info < (3, 10):
    from typing import List, Optional, Union
    from typing_extensions import Literal
else:
    from typing import List, Optional, Union, Literal


class GitGarden:
    """
    A simple tool for automating a recursive scan of local git repos to display their status compared to their
    remote tracking branches with maintenance features such as fetching, pruning, deleting orphaned branches and
    fast-forwarding.

    :param logger: Logger to use for output.
    :param args: Command line arguments.
    :param git: Path to git executable (attempts to resolve system "git" if not passed).
    :raises RuntimeError: If Git installation not found.
    """

    def __init__(
        self,
        logger: logging.Logger,
        args: argparse.Namespace,
        git: Optional[str] = None,
    ) -> None:
        if git is None:
            git = shutil.which("git")
        if git is None or not os.path.exists(git):
            raise RuntimeError("Git installation not found")
        else:
            self.git = git

        self.args = args
        self.logger = logger
        self.pad = _pad = "   "
        self.pad2 = _pad * 2

        if self.args.quiet:
            self.pad = f"{_pad}{dir}: "
            self.pad2 = f"{_pad}{_pad}{dir}: "

        if self.args.quiet:
            for handler in self.logger.handlers:
                if type(handler) is logging.StreamHandler:
                    handler.setLevel(logging.INFO)

        self.colours = Colours()

    def get_dirs_with_depth(self, dir: str, depth: int = 3) -> List[str]:
        """
        Recursively search directories for git repos until a given depth.

        :param dir: Directory to search.
        :param depth: Depth to search.
        :return: Directories containing git repos.
        """
        dir = os.path.expanduser(dir)

        dirs: List[str] = []
        if depth == 0:
            return dirs

        if os.path.isdir(dir):
            dir_base = os.path.basename(dir)
            if dir_base in self.args.exclude:
                return dirs
            if ".git" in os.listdir(dir):
                if self.args.include:
                    if not any([i in dir_base for i in self.args.include]):
                        return dirs
                dirs.append(dir)

        for item in os.listdir(dir):
            item_path = os.path.join(dir, item)
            if os.path.isdir(item_path):
                if depth > 1:
                    subdirs = self.get_dirs_with_depth(
                        item_path,
                        depth - 1,
                    )
                    dirs.extend(subdirs)
        return dirs

    def parse_branches(self, stdout: bytes, upstream: bool = False) -> List[str]:
        """
        Parse the output of a git branch command.

        :param stdout: Output of git branch command.
        :param upstream: Branches include upstream status.
        :return: List of branches.
        """
        # strip current branch marker & padding
        # drop the last element which is always empty
        branches = [
            branch.strip().replace("* ", "") for branch in stdout.decode().split("\n")
        ][:-1]
        if upstream:
            return [
                branch[1:-1].strip() for branch in branches
            ]  # trim additional padding/quote
        else:
            return branches

    def find_current_branch(self, dir: str = ".") -> str:
        """
        Find the current branch name.
        Coverage note: This function can't be tested independently.

        :param dir: Current directory being processed.
        :return: Current branch name.
        """
        local_branches_raw = subprocess.check_output(
            [self.git, "-C", dir, "branch", "--show-current"]
        )
        return local_branches_raw.decode().replace("\n", "")

    def find_root_branch(
        self, local_branches: List[str], remote_branches: List[str]
    ) -> Union[str, None]:
        """
        Attempt to find the root branch (master or main) for a given git repo.

        :param local_branches: List of local branches.
        :param remote_branches: List of remote branches.
        :return: Root branch name.
        """
        root_types = ["master", "main"]
        root_branch: str = ""

        # attempt to find root branch in local + remotes
        for branch in local_branches + remote_branches:
            if root_branch == "":
                for root in root_types:
                    if branch.split()[0] in (root, f"origin/{root}"):
                        root_branch = root
                        break
            else:
                break

        if root_branch == "":
            self.logger.warning(
                f"{self.pad}{self.colours.yellow}Unable to determine root branch{self.colours.clear}"
            )

        return root_branch

    def check_git_status(self, dir: str = ".") -> bool:
        """
        Check status of git working directory.

        :param dir: Current directory being processed.
        :return: Working directory is clean (False) or dirty (True).
        """
        git_status = subprocess.check_output(
            [
                self.git,
                "-C",
                dir,
                "status",
                "--porcelain",
            ]
        )
        return bool(git_status.decode())

    def create_branch(
        self, branch_name: str, root_branch: str = "main", dir: str = "."
    ) -> int:
        """
        Create a branch within a given git repo.

        :param branch_name: Name of the branch to create.
        :param root_branch: Root branch to create from.
        :param dir: Current directory being processed.
        :return: Exit code from branch creation.
        """
        return subprocess.check_call(
            [self.git, "-C", dir, "branch", branch_name, root_branch]
        )

    def delete_branch(
        self,
        branch_name: str,
        dir: str = ".",
        branch_type: Literal["local", "remote", "tracking"] = "local",
    ) -> int:
        """
        Delete a branch within a given git repo.

        :param branch_name: Branch to delete.
        :param dir: Current directory being processed.
        :param branch_type: Specify the branch type for deletion ("local", "remote", "tracking").
        :return: Exit code from branch creation.
        :raises: AttributeError
        """
        # No check_call() as git returns non-zero for non-existent branches
        if branch_type == "remote":
            self.logger.debug(f"{self.pad}Deleting remote branch: {branch_name}")
            return subprocess.run(
                [
                    self.git,
                    "-C",
                    dir,
                    "push",
                    "origin",
                    "--delete",
                    branch_name,
                ]
            ).returncode
        elif branch_type == "tracking":
            self.logger.debug(
                f"{self.pad}Deleting remote tracking branch: {branch_name}"
            )
            return subprocess.run(
                [
                    self.git,
                    "-C",
                    dir,
                    "branch",
                    "-D",
                    "--remote",
                    branch_name,
                ]
            ).returncode
        elif branch_type == "local":
            self.logger.info(f"{self.pad2}Deleting local branch {branch_name}")
            return subprocess.run(
                [
                    self.git,
                    "-C",
                    dir,
                    "branch",
                    "-D",
                    branch_name,
                ]
            ).returncode
        else:
            raise AttributeError(f"Encountered unexpected branch_type: {branch_type}")

    def list_remote_branches(self, dir: str = ".", upstream: bool = False) -> List[str]:
        """
        List remote branches.

        :param dir: Current directory being processed.
        :param upstream: If set include upstream branch status.
        :return: List of remote branches.
        """
        if upstream:
            return self.parse_branches(
                subprocess.check_output(
                    [
                        self.git,
                        "--no-pager",
                        "-C",
                        dir,
                        "branch",
                        "--list",
                        "-r",
                        "origin/*",
                        "--format",
                        "'%(refname:short) %(upstream:short) %(upstream:track)'",
                    ]
                ),
                upstream=upstream,
            )
        return self.parse_branches(
            subprocess.check_output(
                [
                    self.git,
                    "--no-pager",
                    "-C",
                    dir,
                    "branch",
                    "--list",
                    "-r",
                    "origin/*",
                ]
            )
        )

    def list_local_branches(self, dir: str = ".", upstream: bool = False) -> List[str]:
        """
        List local branches (and optionally their upstream branch status).

        :param dir: Current directory being processed.
        :param upstream: If set include upstream branch status.
        :return: List of local branches.
        """
        if upstream:
            return self.parse_branches(
                subprocess.check_output(
                    [
                        self.git,
                        "--no-pager",
                        "-C",
                        dir,
                        "branch",
                        "--format",
                        "'%(refname:short) %(upstream:short) %(upstream:track)'",
                    ]
                ),
                upstream=upstream,
            )
        else:
            return self.parse_branches(
                subprocess.check_output([self.git, "--no-pager", "-C", dir, "branch"])
            )

    def purge_remote_branches(self, dir: str = ".") -> None:
        """
        Recursively purge all remote tracking branches from a given git repo.

        :param dir: Current directory being processed.
        """
        self.logger.info(f"Purging ALL remote tracking branches from {dir}")

        # trying to batch the delete without rate limiting will crash git on very large repos
        for branch in self.list_remote_branches(dir):
            if branch == "origin":
                continue
            self.delete_branch(branch, dir=dir, branch_type="tracking")

    def fetch(self, dir: str = ".", prune: bool = True) -> subprocess.CompletedProcess:
        """
        Fetch (and optionally prune) remote tracking branches from a given git repo.

        :param dir: Current directory being processed.
        :param prune: If set prune remote tracking branches, otherwise fetch only.
        :return: CompletedProcess result from fetch.
        """
        # not checking return code as subprocess errors are expected for non-repo folders
        if prune:
            self.logger.debug(f"Fetching & pruning {dir}")

            return subprocess.run(
                [self.git, "-C", dir, "fetch", "--prune"],
                capture_output=True,
            )
        else:
            self.logger.debug(f"Fetching {dir}")
            return subprocess.run([self.git, "-C", dir, "fetch"], capture_output=True)

    def switch_branch(self, branch: str, dir: str = ".") -> Union[bytes, None]:
        """
        Switch to a branch.

        :param branch: Branch to push.
        :param dir: Current directory being processed.
        :return: CompletedProcess result from switch.
        """
        if not self.check_git_status():
            return subprocess.check_output(
                [
                    self.git,
                    "-C",
                    dir,
                    "switch",
                    branch,
                ]
            )
        else:
            self.logger.warning(
                f"{self.pad2}{self.colours.yellow}Switching precluded by uncommitted changes on current branch"
                f"{self.colours.clear}"
            )
            return None

    def create_commit(self, message: str, dir: str = ".") -> None:
        """
        Create a commit on the local branch.

        :param message: Commit message.
        :param dir: Current directory being processed.
        """
        subprocess.check_call(
            [self.git, "-C", dir, "commit", "--allow-empty", "-m", message]
        )

    def delete_commit(self, dir: str = ".") -> None:
        """
        Delete the most recent commit on the local branch.

        :param dir: Current directory being processed.
        """
        subprocess.check_call([self.git, "-C", dir, "reset", "HEAD~", "--hard"])

    def push_branch(self, branch: str, force: bool = False, dir: str = ".") -> None:
        """
        Push a branch to the remote.

        :param branch: Branch to push.
        :param force: Switch for force push.
        :param dir: Current directory being processed.
        """
        if force:
            subprocess.check_call(
                [
                    self.git,
                    "-C",
                    dir,
                    "push",
                    "-u",
                    "origin",
                    branch,
                    "--force",
                ]
            )
        else:
            subprocess.check_call([self.git, "-C", dir, "push", "-u", "origin", branch])

    def fast_forward_branch(self, current_branch: str, root_branch: str) -> subprocess.CompletedProcess:
        """
        Attempt to fast-forward the current branch.
        Failure to fast-forward is not considered fatal.

        :param current_branch:
        :param root_branch:
        """
        if current_branch == root_branch:
            return subprocess.run(
                [self.git, "-C", dir, "pull", "--ff-only"],
                capture_output=True,
            )
        else:
            # equivalent to a pull -ff-only (only works on non-current branch)
            return subprocess.run(
                [
                    self.git,
                    "-C",
                    dir,
                    "fetch",
                    "origin",
                    f"{root_branch}:{root_branch}",
                ],
                capture_output=True,
            )

    def check_branch_remote_only(
        self, branch: str, local_branches: List[str], remote_branches: List[str]
    ) -> bool:
        """
        :param branch: Branch to check.
        :param local_branches: List of local branches.
        :param remote_branches: List of remote branches.
        :return: Whether the branch only exists on the remote or not.
        """
        basename = branch.split("origin/")[-1]
        if basename not in local_branches and branch in remote_branches:
            return True
        else:
            return False

    def main(self, dirs: List[str]) -> None:
        """
        Execute the main logic of the script.

        :param dirs: Directories containing git repos.
        """
        for dir in dirs:
            if self.args.purge:
                self.purge_remote_branches(dir)
            if self.args.no_fetch:
                self.logger.debug(f"Scanning {dir}")
            elif self.args.no_prune:
                proc = self.fetch(dir, prune=False)
            else:
                proc = self.fetch(dir)

            if not self.args.no_fetch:
                if proc.stderr.decode().startswith("fatal: not a git repository"):
                    continue

            local_branches = self.list_local_branches(dir)
            local_branches_status = self.list_local_branches(dir, upstream=True)

            remote_branches = self.list_remote_branches(dir)

            root_branch = self.find_root_branch(local_branches, remote_branches)
            current_branch = self.find_current_branch(dir)

            if root_branch is None or current_branch is None:
                if self.args.ff:
                    self.logger.warning(
                        f"{self.pad}{self.colours.yellow}--ff will be skipped{self.colours.clear}"
                    )
                if self.args.delete:
                    self.logger.warning(
                        f"{self.pad}{self.colours.yellow}--delete will be skipped{self.colours.clear}"
                    )

            for branch in local_branches_status:
                branch_name = branch.split()[0]
                status = "[" + branch.split("[")[-1]

                if "HEAD" in branch:
                    self.logger.info(
                        f"{self.pad}{self.colours.yellow}{branch_name}{self.colours.clear}"
                    )
                elif "origin" not in branch:
                    self.logger.info(
                        f"{self.pad}{self.colours.yellow}{branch_name} [local only]{self.colours.clear}"
                    )
                elif "[ahead" in branch:
                    self.logger.debug(
                        f"{self.pad}{self.colours.yellow}{branch_name} {status}]{self.colours.clear}"
                    )

                elif "[behind" in branch:
                    if self.args.ff and branch_name == root_branch:
                        self.logger.info(
                            f"{self.pad}{self.colours.yellow}{branch_name} {status}{self.colours.clear}"
                        )
                        self.logger.info(f"{self.pad2}Fast-forwarding {branch_name}")                       
                        ff_result = self.fast_forward_branch(current_branch, root_branch)

                        if ff_result.returncode != 0:
                            self.logger.error(
                                f"{self.pad2}{self.colours.red}Unable to fast-forward {branch_name}{self.colours.clear}"
                            )
                            self.logger.error(
                                f"{self.pad2}{self.colours.red}{ff_result.stderr.decode()}{self.colours.clear}"
                            )
                    else:
                        self.logger.debug(
                            f"{self.pad}{self.colours.yellow}{branch_name} {status}{self.colours.clear}"
                        )

                elif "[gone" in branch:
                    self.logger.info(
                        f"{self.pad}{self.colours.red}{branch_name} [remote deleted]{self.colours.clear}"
                    )
                    if self.args.delete:
                        safe_to_delete = True
                        if current_branch == branch_name:
                            safe_to_delete = False
                            self.logger.debug(
                                f"{self.pad2}Switching from {current_branch} to {root_branch}"
                            )
                            switch_result = self.switch_branch(branch, dir=dir)

                            if switch_result is None:
                                self.logger.warning(
                                    f"{self.pad2}{self.colours.yellow}Skipping delete of {branch_name}"
                                    f"{self.colours.clear}"
                                )
                            else:
                                safe_to_delete = True
                                current_branch = (
                                    root_branch if root_branch is not None else ""
                                )

                        if safe_to_delete:
                            self.delete_branch(branch_name, dir=dir)

                else:
                    self.logger.debug(
                        f"{self.pad}{self.colours.green}{branch_name} [up to date]{self.colours.clear}"
                    )

            if self.args.remote:
                for remote_branch in remote_branches:
                    if "/HEAD" in remote_branch:
                        continue
                    if self.check_branch_remote_only(
                        remote_branch, local_branches, remote_branches
                    ):
                        self.logger.info(
                            f"{self.pad}{self.colours.yellow}{branch.split('origin/')[-1]} [remote only]{self.colours.clear}"
                        )


class Colours:
    """
    May require calling os.system("color") to enable ANSI codes on Windows.
    Colour table: https://stackoverflow.com/a/21786287/10639133.
    """

    def __init__(self) -> None:
        self.yellow = "\x1b[0;33;40m"
        self.red = "\x1b[0;31;40m"
        self.green = "\x1b[0;32;40m"
        self.clear = "\x1b[0m"
