import os
import logging
import subprocess
import shutil
import argparse

from typing import List


class GitGarden:
    """
    A simple tool for automating a recursive scan of local git repos to display their status compared to their remote
    tracking branches with maintenance features such as fetching, pruning, deleting orphaned branches and
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

    def _get_dirs_with_depth(
        self, dir: str, depth: int, include: List[str], exclude: List[str]
    ) -> List[str]:
        """
        Recursively search directories for git repos until a given depth.

        :param dir: Directory to search.
        :param exclude: Filter results to exclude directories containing these sub-string(s).
        :param depth: Depth to search.
        :param include: Filter results to only include directories containing these sub-string(s).
        :return: Directories containing git repos.
        """
        dirs = []
        if depth == 0:
            return dirs

        if os.path.isdir(dir):
            dir_base = os.path.basename(dir)
            if dir_base in exclude:
                return dirs
            if ".git" in os.listdir(dir):
                if include:
                    if not any([i in dir_base for i in include]):
                        return dirs
                dirs.append(dir)

        for item in os.listdir(dir):
            item_path = os.path.join(dir, item)
            if os.path.isdir(item_path):
                if depth > 1:
                    subdirs = self._get_dirs_with_depth(
                        item_path, depth - 1, include, exclude
                    )
                    dirs.extend(subdirs)
        return dirs

    def _parse_branches(self, stdout: bytes) -> List[str]:
        """
        Parse the output of a git branch command.

        :param stdout: Output of git branch command.
        :return: List of branches.
        """
        return stdout.decode().rstrip().split("\n")

    def _find_current_branch(self, dir: str = ".") -> str:
        """
        Find the current branch name.

        :param dir: Current directory being processed.
        :return: Current branch name.
        """
        current_branch = None
        local_branches_raw = subprocess.check_output(
            [shutil.which("git"), "--no-pager", "-C", dir, "branch"]
        )
        for branch in local_branches_raw.decode().split("\n"):
            if branch.startswith("*"):
                current_branch = branch.split()[-1]
                break
        return current_branch

    def _check_git_status(self, dir: str = ".") -> bool:
        """
        Check status of git working directory.

        :param dir: Current directory being processed.
        :return: Working directory is clean (False) or dirty (True).
        """
        git_status = subprocess.run(
            [
                shutil.which("git"),
                "-C",
                dir,
                "status",
                "--porcelain",
            ],
            capture_output=True,
        )
        return bool(git_status.stdout.decode())

    def _create_branch(
        self, branch_name: str, dir: str = "."
    ) -> subprocess.CompletedProcess:
        """
        Create a branch within a given git repo.

        :param branch_name: Name of the branch to create.
        :param dir: Current directory being processed.
        :return: CompletedProcess result from branch creation.
        """
        return subprocess.run(
            [
                shutil.which("git"),
                "-C",
                dir,
                "branch",
                "-c",
                branch_name,
            ],
            capture_output=True,
        )

    def _delete_branch(
        self, branch_name: str, dir: str = "."
    ) -> subprocess.CompletedProcess:
        """
        Delete a branch within a given git repo.

        :param dir: Current directory being processed.
        :param branch_name: Branch to delete.
        :return: CompletedProcess result from branch deletion.
        """
        return subprocess.run(
            [
                shutil.which("git"),
                "-C",
                dir,
                "branch",
                "-D",
                branch_name,
            ],
            capture_output=True,
        )

    def _purge_remote_branches(self, dir: str = ".") -> None:
        """
        Recursively purge all remote tracking branches from a given git repo.

        :param dir: Current directory being processed.
        """
        self.logger.info(f"Purging ALL remote tracking branches from {dir}")
        proc = subprocess.check_output(
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
                "%(refname:short)",
            ]
        )

        # trying to batch the delete without rate limiting will crash git on very large repos
        for branch in self._parse_branches(proc):
            if branch == "origin":
                continue
            if branch:
                self.logger.debug(
                    f"{self.pad}Deleting remote tracking branch: {branch}"
                )
                subprocess.check_call(
                    [
                        shutil.which("git"),
                        "-C",
                        dir,
                        "branch",
                        "-r",
                        "-D",
                        branch,
                    ]
                )

    def _main(self, dirs: List[str], args: argparse.Namespace) -> None:
        """
        Execute the main logic of the script

        :param dirs: Directories containing git repos
        :param args: Command line arguments
        """
        for dir in dirs:
            if args.purge:
                self._purge_remote_branches(dir)
            if args.no_fetch:
                self.logger.debug(f"Scanning {dir}")
            elif args.no_prune:
                self.logger.debug(f"Fetching {dir}")
                # not checking return code as errors are expected for non-repo folders
                proc = subprocess.run(
                    [shutil.which("git"), "-C", dir, "fetch"], capture_output=True
                )
            else:
                self.logger.debug(f"Fetching & pruning {dir}")
                # not checking return code as errors are expected for non-repo folders
                proc = subprocess.run(
                    [shutil.which("git"), "-C", dir, "fetch", "--prune"],
                    capture_output=True,
                )

            if not args.no_fetch:
                if proc.stderr.decode().startswith("fatal: not a git repository"):
                    continue

            local_branches = self._parse_branches(
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
                )
            )

            remote_branches = self._parse_branches(
                subprocess.check_output(
                    [shutil.which("git"), "--no-pager", "-C", dir, "branch", "--remote"]
                )
            )
            root_branch = None
            for branch in remote_branches:
                if branch:
                    if branch.split()[0] == "origin/master":
                        root_branch = "master"
                        break
                    elif branch.split()[0] == "origin/main":
                        root_branch = "main"
                        break

            if root_branch is None:
                for branch in local_branches:
                    if branch:
                        if branch.split()[0] == "master":
                            root_branch = "master"
                            break
                        elif branch.split()[0] == "main":
                            root_branch = "main"
                            break

            current_branch = self._find_current_branch(dir)

            if current_branch is None:
                self.logger.warning(
                    f"{self.pad}{Colours.yellow}Unable to determine current branch{Colours.clear}"
                )
            if root_branch is None:
                self.logger.warning(
                    f"{self.pad}{Colours.yellow}Unable to determine root branch{Colours.clear}"
                )
            if root_branch is None or current_branch is None:
                if args.ff:
                    self.logger.warning(
                        f"{self.pad}{Colours.yellow}--ff will be skipped{Colours.clear}"
                    )
                if args.delete:
                    self.logger.warning(
                        f"{self.pad}{Colours.yellow}--delete will be skipped{Colours.clear}"
                    )

            for branch in local_branches:
                branch_name = branch.split()[0].replace("'", "", 1)
                status = "[" + branch.split("[")[-1].replace("'", "")

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
                    if args.ff and branch_name == root_branch:
                        self.logger.info(
                            f"{self.pad}{Colours.yellow}{branch_name} {status}{Colours.clear}"
                        )
                        self.logger.info(f"{self.pad2}Fast-forwarding {branch_name}")

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
                    if args.delete:
                        safe_to_delete = True
                        if current_branch == branch_name:
                            if self._check_git_status(dir):
                                safe_to_delete = False
                                self.logger.warning(
                                    f"{self.pad2}{Colours.yellow}Switching precluded by uncommitted changes on "
                                    f"current branch - skipping delete of {branch_name}{Colours.clear}"
                                )
                            else:
                                self.logger.debug(
                                    f"{self.pad2}Switching from {current_branch} to {root_branch}"
                                )
                                switch_result = subprocess.run(
                                    [
                                        shutil.which("git"),
                                        "-C",
                                        dir,
                                        "switch",
                                        root_branch,
                                    ],
                                    capture_output=True,
                                )

                                if switch_result.returncode != 0:
                                    safe_to_delete = False
                                    self.logger.error(
                                        f"{self.pad2}{Colours.red}Switch failed, skipping delete of "
                                        f"{branch_name}{Colours.clear}"
                                    )
                                    self.logger.error(
                                        f"{self.pad}{Colours.red}{switch_result.stderr.decode()}{Colours.clear}"
                                    )
                                else:
                                    current_branch = root_branch

                        if safe_to_delete:
                            self.logger.info(
                                f"{self.pad2}Deleting local branch {branch_name}"
                            )
                            del_result = self._delete_branch(branch_name, dir=dir)
                            if del_result.returncode != 0:
                                self.logger.error(
                                    f"{self.pad}{Colours.red}Unable to delete {branch_name}{Colours.clear}"
                                )
                                self.logger.error(
                                    f"{self.pad}{Colours.red}{del_result.stderr.decode()}{Colours.clear}"
                                )
                else:
                    self.logger.debug(
                        f"{self.pad}{Colours.green}{branch_name} [up to date]{Colours.clear}"
                    )

            if args.remote:
                for remote_branch in remote_branches:
                    if "/HEAD" in remote_branch:
                        continue
                    basename = remote_branch.split("origin/")[-1]
                    if basename not in [
                        b.split()[0].rstrip().replace("'", "", 1)
                        for b in local_branches
                    ]:
                        self.logger.info(
                            f"{self.pad}{Colours.yellow}{basename} [remote only]{Colours.clear}"
                        )


class CustomFormatter(logging.Formatter):
    """
    Custom formatter for logging, allowing parsing of log messages.

    This formatter extends the base logging.Formatter and provides a method
    for custom parsing of log messages before they are emitted.

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
    May require calling os.system("color") to enable ANSI codes on Windows
    Colour table: https://stackoverflow.com/a/21786287/10639133
    """

    yellow = "\x1b[0;33;40m"
    red = "\x1b[0;31;40m"
    green = "\x1b[0;32;40m"
    clear = "\x1b[0m"
