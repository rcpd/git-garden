import os
import logging
import subprocess
import shutil
import argparse
from typing import List, Optional, Literal, cast


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

        # args will not exist in test init
        if "root" not in args or not args.root:
            args.root = ["main", "master"]

        self.git = git
        self.args = args
        self.logger = logger
        self.pad = _pad = "   "
        self.pad2 = _pad * 2
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

    def parse_branches(self, stdout: str, upstream: bool = False) -> List[str]:
        """
        Parse the output of a git branch command.

        :param stdout: Output of git branch command.
        :param upstream: Branches include upstream status.
        :return: List of branches.
        """
        # strip current branch marker & padding
        # drop the last element which is always empty
        branches = [branch.strip().replace("* ", "") for branch in stdout.split("\n")][:-1]
        if upstream:
            return [branch[1:-1].strip() for branch in branches]  # trim additional padding/quote
        else:
            return branches

    def run_and_log(self, proc_args: List[str], check: bool = True, capture: bool = True) -> int | str:
        """
        Call subprocess.run() and passthrough args & check, returning either the output or the return code.
        Defaults to same behaviour as subprocess.check_output() (raise on non-zero, return stdout)
        In all cases log the result to debug.

        :param proc_args: The process arguments for subprocess.run().
        :param check: Whether to raise on non-zero return or not.
        :param capture: Whether to return output or return code.
        :return: Output (str) or return code (int)
        """
        self.logger.debug(f"Running command: {proc_args}")
        proc = subprocess.run(proc_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check, text=True)

        stdout = proc.stdout
        stderr = proc.stderr

        self.logger.debug(f"Stdout: {stdout}")
        self.logger.debug(f"Stderr: {stderr}")
        self.logger.debug(f"Return code: {proc.returncode}")

        if capture:
            return proc.stdout
        else:
            return proc.returncode

    def find_current_branch(self, dir: str = ".") -> str:
        """
        Find the current branch name.
        Coverage note: This function can't be tested independently.

        :param dir: Current directory being processed.
        :return: Current branch name.
        """
        local_branches_raw = self.run_and_log([self.git, "-C", dir, "branch", "--show-current"])
        return cast(str, local_branches_raw).replace("\n", "")

    def find_root_branch(self, local_branches: List[str], remote_branches: List[str]) -> str:
        """
        Attempt to find the root branch (main, master or --root) for a given git repo.

        :param local_branches: List of local branches.
        :param remote_branches: List of remote branches.
        :return: Root branch name.
        """
        root_branch: str = ""

        # attempt to find root branch in local + remotes
        for branch in local_branches + remote_branches:
            if root_branch == "":
                for root in self.args.root:
                    if branch.split()[0] in (root, f"origin/{root}"):
                        root_branch = root
                        break
            else:
                break

        if root_branch == "":
            self.logger.warning(f"{self.pad}{self.colours.yellow}Unable to determine root branch{self.colours.clear}")

        return root_branch

    def check_git_status(self, dir: str = ".") -> bool:
        """
        Check status of git working directory.

        :param dir: Current directory being processed.
        :return: Working directory is clean (False) or dirty (True).
        """
        git_status = self.run_and_log(
            [
                self.git,
                "-C",
                dir,
                "status",
                "--porcelain",
            ]
        )
        return bool(git_status)

    def create_branch(self, branch_name: str, root_branch: str = "main", dir: str = ".") -> int:
        """
        Create a branch within a given git repo.

        :param branch_name: Name of the branch to create.
        :param root_branch: Root branch to create from.
        :param dir: Current directory being processed.
        :return: Exit code from branch creation.
        """
        return cast(int, self.run_and_log([self.git, "-C", dir, "branch", branch_name, root_branch], capture=False))

    def delete_branch(
        self,
        branch_name: str,
        dir: str = ".",
        branch_type: Literal["local", "remote", "tracking", "all"] = "local",
    ) -> int:
        """
        Delete a branch within a given git repo.

        :param branch_name: Branch to delete.
        :param dir: Current directory being processed.
        :param branch_type: Specify the branch type for deletion.
        :return: Exit code from branch deletion, 0 if branch not found.
        :raises ValueError: on unexpected branch_type.
        """
        if branch_type in ("local", "all"):
            local_branches = self.list_local_branches(dir)
        if branch_type in ("remote", "tracking", "all"):
            remote_branches = self.list_remote_branches(dir)
        if branch_type not in ("local", "remote", "tracking", "all"):
            raise ValueError(f"Encountered unexpected branch_type: {branch_type}")

        if branch_type == "remote" and "origin/" + branch_name in remote_branches:
            self.logger.info(f"{self.pad}Deleting remote branch: {branch_name}")
            return cast(
                int,
                self.run_and_log(
                    [
                        self.git,
                        "-C",
                        dir,
                        "push",
                        "origin",
                        "--delete",
                        branch_name,
                    ],
                    capture=False,
                ),
            )
        elif branch_type == "tracking" and branch_name in remote_branches:
            self.logger.info(f"{self.pad}Deleting remote tracking branch: {branch_name}")
            return cast(
                int,
                self.run_and_log(
                    [
                        self.git,
                        "-C",
                        dir,
                        "branch",
                        "-D",
                        "--remote",
                        branch_name,
                    ],
                    capture=False,
                ),
            )
        elif branch_type == "local" and branch_name in local_branches:
            self.logger.info(f"{self.pad2}Deleting local branch {branch_name}")
            return cast(
                int,
                self.run_and_log(
                    [
                        self.git,
                        "-C",
                        dir,
                        "branch",
                        "-D",
                        branch_name,
                    ],
                    capture=False,
                ),
            )
        elif branch_type == "all":
            returncode = self.delete_branch(branch_name, dir=dir, branch_type="local")
            returncode += self.delete_branch(branch_name, dir=dir, branch_type="remote")
            returncode += self.delete_branch(branch_name, dir=dir, branch_type="tracking")
            return returncode

        return 0  # emulate success if branch not found

    def list_remote_branches(self, dir: str = ".", upstream: bool = False) -> List[str]:
        """
        List remote branches.

        :param dir: Current directory being processed.
        :param upstream: If set include upstream branch status.
        :return: List of remote branches.
        """
        if upstream:
            return self.parse_branches(
                cast(
                    str,
                    self.run_and_log(
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
                ),
                upstream=upstream,
            )
        return self.parse_branches(
            cast(
                str,
                self.run_and_log(
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
                ),
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
                cast(
                    str,
                    self.run_and_log(
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
                ),
                upstream=upstream,
            )
        else:
            return self.parse_branches(cast(str, self.run_and_log([self.git, "--no-pager", "-C", dir, "branch"])))

    def purge_tracking_branches(self, dir: str = ".") -> None:
        """
        Recursively purge all remote tracking branches from a given git repo.

        :param dir: Current directory being processed.
        """
        self.logger.info(f"Purging ALL remote tracking branches from {dir}")

        # trying to batch the delete without rate limiting will crash git on very large repos
        for branch in self.list_remote_branches(dir):
            if not branch.startswith("origin/HEAD"):
                self.delete_branch(branch, dir=dir, branch_type="tracking")

    def fetch(self, dir: str = ".", prune: bool = True) -> None:
        """
        Fetch (and optionally prune) remote tracking branches from a given git repo.

        :param dir: Current directory being processed.
        :param prune: If set prune remote tracking branches, otherwise fetch only.
        """
        if prune:
            self.logger.info(f"Fetching & pruning {dir}")
            self.run_and_log([self.git, "-C", dir, "fetch", "--prune"], capture=False)
        else:
            self.logger.info(f"Fetching {dir}")
            self.run_and_log([self.git, "-C", dir, "fetch"], capture=False)

    def switch_branch(self, branch: str, dir: str = ".") -> str | None:
        """
        Switch to a branch.

        :param branch: Branch to push.
        :param dir: Current directory being processed.
        :return: Result from branch switch (stdout or None if skipped).
        """
        if not self.check_git_status(dir):
            return cast(
                str,
                self.run_and_log(
                    [
                        self.git,
                        "-C",
                        dir,
                        "switch",
                        branch,
                    ]
                ),
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
        self.run_and_log([self.git, "-C", dir, "commit", "--allow-empty", "-m", message], capture=False)

    def delete_commit(self, dir: str = ".") -> None:
        """
        Delete the most recent commit on the local branch.

        :param dir: Current directory being processed.
        """
        self.run_and_log([self.git, "-C", dir, "reset", "HEAD~", "--hard"], capture=False)

    def push_branch(self, branch: str, force: bool = False, dir: str = ".") -> None:
        """
        Push a branch to the remote.

        :param branch: Branch to push.
        :param force: Switch for force push.
        :param dir: Current directory being processed.
        """
        if force:
            self.run_and_log(
                [
                    self.git,
                    "-C",
                    dir,
                    "push",
                    "-u",
                    "origin",
                    branch,
                    "--force",
                ],
                capture=False,
            )
        else:
            self.run_and_log([self.git, "-C", dir, "push", "-u", "origin", branch], capture=False)

    def fast_forward_branch(self, dir: str = ".") -> int:
        """
        Attempt to fast-forward the current branch.
        Failure to fast-forward is not considered fatal.

        :param dir: Current directory being processed.
        :return: Return code from fast-forward.
        """
        # this is a rare exception where a failing git command will not be considered fatal
        return cast(int, self.run_and_log([self.git, "-C", dir, "pull", "--ff-only"], check=False, capture=False))

    def pull_non_current_branch(self, branch: str, dir: str = ".") -> int:
        """
        :param branch: Branch to fetch.
        :param dir: Current directory being processed.
        :return: Return code from fetch.
        """
        # this is a rare exception where a failing git command will not be considered fatal
        return cast(int, self.run_and_log([self.git, "-C", dir, "fetch", "origin", f"{branch}:{branch}"]))

    def check_branch_remote_only(self, branch: str, local_branches: List[str], remote_branches: List[str]) -> bool:
        """
        Check whether branch only exists on the remote.

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
                self.purge_tracking_branches(dir)
            if self.args.no_fetch:
                self.logger.info(f"Scanning {dir}")
            else:
                self.fetch(dir, prune=(not self.args.no_prune))

            local_branches = self.list_local_branches(dir)
            local_branches_status = self.list_local_branches(dir, upstream=True)

            remote_branches = self.list_remote_branches(dir)

            root_branch = self.find_root_branch(local_branches, remote_branches)
            current_branch = self.find_current_branch(dir)

            if root_branch == "":  # pragma: no cover # logs only
                if self.args.ff:
                    self.logger.warning(f"{self.pad}{self.colours.yellow}--ff will be skipped{self.colours.clear}")
                if self.args.delete:
                    self.logger.warning(f"{self.pad}{self.colours.yellow}--delete will be skipped{self.colours.clear}")

            for branch in local_branches_status:
                branch_name = branch.split()[0]
                status = "[" + branch.split("[")[-1]

                if "HEAD" in branch:  # pragma: no cover # logs only
                    self.logger.info(f"{self.pad}{self.colours.yellow}{branch_name}{self.colours.clear}")
                elif "origin" not in branch:  # pragma: no cover # logs only
                    self.logger.info(f"{self.pad}{self.colours.yellow}{branch_name} [local only]{self.colours.clear}")
                elif "[ahead" in branch:  # pragma: no cover # logs only
                    self.logger.info(f"{self.pad}{self.colours.yellow}{branch_name} {status}]{self.colours.clear}")

                elif "[behind" in branch:  # pragma: no cover # ff tested seperately
                    self.logger.info(f"{self.pad}{self.colours.yellow}{branch_name} {status}{self.colours.clear}")
                    if self.args.ff or self.args.ff_all:
                        self.logger.info(f"{self.pad2}Fast-forwarding {branch_name}")
                        if current_branch == root_branch == branch_name:
                            error = self.fast_forward_branch(dir=dir)  # typical --ff-only pull
                        elif self.args.ff_all:
                            error = self.pull_non_current_branch(branch_name, dir=dir)  # fetch origin src:dest
                        else:
                            error = None

                        if error:
                            self.logger.error(
                                f"{self.pad2}{self.colours.red}Unable to fast-forward {branch_name}, "
                                f"check debug logs for details.{self.colours.clear}"
                            )

                elif "[gone]" in branch:  # pragma: no cover # funcs tested seperately
                    self.logger.info(f"{self.pad}{self.colours.red}{branch_name} [remote deleted]{self.colours.clear}")
                    if self.args.delete and root_branch:
                        if current_branch == branch_name:
                            self.logger.info(f"{self.pad2}Switching from {current_branch} to {root_branch}")

                            switch_result = self.switch_branch(root_branch, dir=dir)
                            current_branch = self.find_current_branch(dir)

                            if switch_result is None:
                                self.logger.warning(
                                    f"{self.pad2}{self.colours.yellow}Skipping delete of {branch_name}"
                                    f"{self.colours.clear}"
                                )
                                continue

                        self.delete_branch(branch_name, dir=dir)

                else:  # pragma: no cover # logs only
                    self.logger.info(f"{self.pad}{self.colours.green}{branch_name} [up to date]{self.colours.clear}")

            if self.args.remote:  # pragma: no cover, cannot repro / remote_only tested seperately
                for remote_branch in remote_branches:
                    if "/HEAD" in remote_branch:
                        continue
                    if self.check_branch_remote_only(remote_branch, local_branches, remote_branches):
                        self.logger.info(
                            f"{self.pad}{self.colours.yellow}{remote_branch.split('origin/')[-1]} [remote only]"
                            f"{self.colours.clear}"
                        )


class Colours:
    """
    May require calling os.system("color") to enable ANSI codes on Windows.
    Colour table: https://stackoverflow.com/a/21786287/10639133.
    """

    def __init__(self) -> None:
        self.yellow = "\x1b[33m"
        self.red = "\x1b[31m"
        self.green = "\x1b[32m"
        self.clear = "\x1b[0m"
