import os
import logging
import subprocess
import shutil
import argparse

from typing import List


class GitGarden:
    """
    A simple tool for automating a recursive scan of local git repos to display their status compared to their
    remote tracking branches with maintenance features such as fetching, pruning, deleting orphaned branches and
    fast-forwarding.

    :param logger: Logger to use for output.
    :param args: Command line arguments.
    """

    def __init__(self, logger: logging.Logger, args: argparse.Namespace) -> None:
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

    def get_dirs_with_depth(self, dir: str, depth: int = 3) -> List[str]:
        """
        Recursively search directories for git repos until a given depth.

        :param dir: Directory to search.
        :param depth: Depth to search.
        :return: Directories containing git repos.
        """
        dir = os.path.expanduser(dir)

        dirs = []
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
                branch[1:-2] for branch in branches
            ]  # trim additional padding/quote
        else:
            return branches

    def find_current_branch(self, dir: str = ".") -> str:
        """
        Find the current branch name.

        :param dir: Current directory being processed.
        :return: Current branch name.
        """
        local_branches_raw = subprocess.check_output(
            [shutil.which("git"), "-C", dir, "branch", "--show-current"]
        )
        return local_branches_raw.decode().replace("\n", "")

    def find_root_branch(
        self, local_branches: List[str], remote_branches: List[str]
    ) -> str:
        """
        Attempt to find the root branch (master or main) for a given git repo.

        :param local_branches: List of local branches.
        :param remote_branches: List of remote branches.
        :return: Root branch name.
        """
        root_branch = None
        for branch in remote_branches:
            if branch.split()[0] == "origin/master":
                root_branch = "master"
                break
            elif branch.split()[0] == "origin/main":
                root_branch = "main"
                break

        if root_branch is None:
            for branch in local_branches:
                if branch.split()[0] == "master":
                    root_branch = "master"
                    break
                elif branch.split()[0] == "main":
                    root_branch = "main"
                    break

        if root_branch is None:
            self.logger.warning(
                f"{self.pad}{Colours.yellow}Unable to determine root branch{Colours.clear}"
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
                shutil.which("git"),
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
            [shutil.which("git"), "-C", dir, "branch", branch_name, root_branch]
        )

    # TODO: delete remote branch
    def delete_branch(
        self, branch_name: str, dir: str = ".", remote: bool = False
    ) -> int:
        """
        Delete a branch within a given git repo.

        :param branch_name: Branch to delete.
        :param dir: Current directory being processed.
        :param remote: If set delete a remote tracking branch, otherwise delete the local branch.
        :return: Exit code from branch creation.
        """
        if remote:
            self.logger.debug(
                f"{self.pad}Deleting remote tracking branch: {branch_name}"
            )
            return subprocess.check_call(
                [
                    shutil.which("git"),
                    "-C",
                    dir,
                    "branch",
                    "-r",
                    "-D",
                    branch_name,
                ]
            )
        else:
            self.logger.info(f"{self.pad2}Deleting local branch {branch_name}")
            return subprocess.check_call(
                [
                    shutil.which("git"),
                    "-C",
                    dir,
                    "branch",
                    "-D",
                    branch_name,
                ]
            )

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
                        shutil.which("git"),
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
                )
            )
        return self.parse_branches(
            subprocess.check_output(
                [
                    shutil.which("git"),
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
                        shutil.which("git"),
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
                subprocess.check_output(
                    [shutil.which("git"), "--no-pager", "-C", dir, "branch"]
                )
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
            self.delete_branch(branch, dir=dir, remote=True)

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
                [shutil.which("git"), "-C", dir, "fetch", "--prune"],
                capture_output=True,
            )
        else:
            self.logger.debug(f"Fetching {dir}")
            return subprocess.run(
                [shutil.which("git"), "-C", dir, "fetch"], capture_output=True
            )

    def switch_branch(self, branch: str, dir: str = ".") -> subprocess.CompletedProcess:
        """
        Switch to a branch.

        :param dir: Current directory being processed.
        :param branch: Branch to push.
        :return: CompletedProcess result from switch.
        """
        if not self.check_git_status():
            return subprocess.check_output(
                [
                    shutil.which("git"),
                    "-C",
                    dir,
                    "switch",
                    branch,
                ]
            )
        else:
            self.logger.warning(
                f"{self.pad2}{Colours.yellow}Switching precluded by uncommitted changes on "
                f"current branch{Colours.clear}"
            )

    def create_commit(self, message: str, dir: str = ".") -> None:
        """
        Create a commit on a branch.

        :param gg: GitGarden instance.
        :param dir: Current directory being processed.
        :param branch: Branch to push.
        """
        subprocess.check_call(
            [shutil.which("git"), "-C", dir, "commit", "--allow-empty", "-m", message]
        )

    def push_branch(self, branch: str, force: bool = False, dir: str = ".") -> None:
        """
        Push a branch to the remote.

        :param branch: Branch to push.
        :param dir: Current directory being processed.

        """
        if force:
            subprocess.check_call(
                [shutil.which("git"), "-C", dir, "push", "origin", branch, "--force"]
            )
        else:
            subprocess.check_call(
                [
                    shutil.which("git"),
                    "-C",
                    dir,
                    "push",
                    "origin",
                    branch,
                ]
            )

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
            # remote_branches_status = self.list_remote_branches(dir, upstream=True) # FIXME: unused

            root_branch = self.find_root_branch(local_branches, remote_branches)
            current_branch = self.find_current_branch(dir)

            if root_branch is None or current_branch is None:
                if self.args.ff:
                    self.logger.warning(
                        f"{self.pad}{Colours.yellow}--ff will be skipped{Colours.clear}"
                    )
                if self.args.delete:
                    self.logger.warning(
                        f"{self.pad}{Colours.yellow}--delete will be skipped{Colours.clear}"
                    )

            for branch in local_branches_status:
                branch_name = branch.split()[0]
                status = "[" + branch.split("[")[-1]

                if "HEAD" in branch:
                    self.logger.info(
                        f"{self.pad}{Colours.yellow}{branch_name}{Colours.clear}"
                    )
                elif "origin" not in branch:
                    self.logger.info(
                        f"{self.pad}{Colours.yellow}{branch_name} [local only]{Colours.clear}"
                    )
                elif "[ahead" in branch:
                    self.logger.debug(
                        f"{self.pad}{Colours.yellow}{branch_name} {status}"
                    )

                elif "[behind" in branch:
                    if self.args.ff and branch_name == root_branch:
                        self.logger.info(
                            f"{self.pad}{Colours.yellow}{branch_name} {status}{Colours.clear}"
                        )
                        self.logger.info(f"{self.pad2}Fast-forwarding {branch_name}")

                        # attempt to fast-forward the current branch
                        # ff failure is not fatal (logged below)
                        if current_branch == root_branch:
                            ff_result = subprocess.run(
                                [shutil.which("git"), "-C", dir, "pull", "--ff-only"],
                                capture_output=True,
                            )
                        else:
                            # equivalent to a pull -ff-only (only works on non-current branch)
                            ff_result = subprocess.run(
                                [
                                    shutil.which("git"),
                                    "-C",
                                    dir,
                                    "fetch",
                                    "origin",
                                    f"{root_branch}:{root_branch}",
                                ],
                                capture_output=True,
                            )

                        if ff_result.returncode != 0:
                            self.logger.error(
                                f"{self.pad2}{Colours.red}Unable to fast-forward {branch_name}{Colours.clear}"
                            )
                            self.logger.error(
                                f"{self.pad2}{Colours.red}{ff_result.stderr.decode()}{Colours.clear}"
                            )
                    else:
                        self.logger.debug(
                            f"{self.pad}{Colours.yellow}{branch_name} {status}{Colours.clear}"
                        )

                elif "[gone]" in branch:
                    self.logger.info(
                        f"{self.pad}{Colours.red}{branch_name} [remote deleted]{Colours.clear}"
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
                                    f"{self.pad2}{Colours.yellow}Skipping delete of {branch_name}{Colours.clear}"
                                )
                            else:
                                safe_to_delete = True
                                current_branch = root_branch

                        if safe_to_delete:
                            self.delete_branch(branch_name, dir=dir)

                else:
                    self.logger.debug(
                        f"{self.pad}{Colours.green}{branch_name} [up to date]{Colours.clear}"
                    )

            if self.args.remote:
                for remote_branch in remote_branches:
                    if "/HEAD" in remote_branch:
                        continue
                    basename = remote_branch.split("origin/")[-1]
                    if basename not in [b.split()[0] for b in local_branches_status]:
                        self.logger.info(
                            f"{self.pad}{Colours.yellow}{basename} [remote only]{Colours.clear}"
                        )


class CustomFormatter(logging.Formatter):
    """
    This formatter extends the base logging.Formatter and provides a method for custom parsing of log messages before
    they are emitted.

    :param fmt: The format string for the log message.
    :param datefmt: The format string for the date in the log message.
    :param style: The formatting style ('%' or '{' style).
    """

    def __init__(self, fmt: str, datefmt: str = None, style: str = "{") -> None:
        super().__init__(fmt, datefmt, style)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the specified record, including custom parsing of the log message.

        :param record: The log record to be formatted.
        :return: The formatted log message.
        """
        record.msg = self.strip_colours(record.msg)
        return super().format(record)

    def strip_colours(self, message: str) -> str:
        """
        Strip the ANSI colour codes from the log message.

        :param message: The original log message.
        :return: The parsed log message.
        """
        message = (
            message.replace(Colours.yellow, "")
            .replace(Colours.red, "")
            .replace(Colours.green, "")
        )
        message = message.replace(Colours.clear, "")
        return message


class Colours:
    """
    May require calling os.system("color") to enable ANSI codes on Windows.
    Colour table: https://stackoverflow.com/a/21786287/10639133.
    """

    yellow = "\x1b[0;33;40m"
    red = "\x1b[0;31;40m"
    green = "\x1b[0;32;40m"
    clear = "\x1b[0m"
