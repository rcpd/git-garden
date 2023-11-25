"""
A simple tool for automating a recursive scan of local git repos to display their status compared to their remote 
tracking branches with maintenance features such as fetching, pruning, deleting orphaned branches and fast-forwarding. 
"""

import os
import sys
import subprocess
import shutil
import argparse
import logging
from typing import List

class Colours:
    """
    May require calling os.system("color") to enable ANSI codes on Windows
    Colour table: https://stackoverflow.com/a/21786287/10639133
    """
    yellow = "\x1b[0;33;40m"
    red = "\x1b[0;31;40m"
    green = "\x1b[0;32;40m"
    clear = "\x1b[0m"

class CustomFormatter(logging.Formatter):
    """
    Custom formatter for logging, allowing parsing of log messages.

    This formatter extends the base logging.Formatter and provides a method
    for custom parsing of log messages before they are emitted.

    :param fmt: The format string for the log message.
    :param datefmt: The format string for the date in the log message.
    :param style: The formatting style ('%' or '{' style).
    """

    def __init__(self, fmt: str, datefmt: str = None, style: str = '{') -> None:
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
        message = message.replace(Colours.yellow, "").replace(Colours.red, "").replace(Colours.green, "")
        message = message.replace(Colours.clear, "")
        return message
    
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())  # must be defined before file_handler to avoid formatting clash

file_handler = logging.FileHandler(os.path.join(os.path.dirname(__file__), 'garden.log'), mode="w")
custom_fmtr = CustomFormatter(
    fmt="{asctime} - {name} - {levelname:^5s} - {message}",
    datefmt='%Y-%m-%d %H:%M:%S',
    style="{"
)
file_handler.setFormatter(custom_fmtr)
logger.addHandler(file_handler)


def _get_dirs_with_depth(dir: str, depth: int, include: List[str], exclude: List[str]) -> List[str]:
    """
    Recursively search directories for git repos until a given depth

    :param dir: Directory to search
    :param depth: Depth to search
    :param include: Filter results to only include directories containing these string
    :return: Directories containing git repos
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
                subdirs = _get_dirs_with_depth(item_path, depth-1, include, exclude)
                dirs.extend(subdirs)
    return dirs

def _parse_branches(stdout: bytes) -> List[str]:
    """
    Parse the output of a git branch command

    :param stdout: Output of git branch command
    :return: List of branches
    """
    return stdout.decode().rstrip().split("\n")

def _find_current_branch(dir) -> str:
    """
    Find the current branch name

    :param dir: Current directory being processed
    :return: Current branch name
    """
    current_branch = None
    local_branches_raw = subprocess.check_output([shutil.which("git"), "--no-pager", "-C", dir, "branch"])
    for branch in local_branches_raw.decode().split("\n"):
        if branch.startswith("*"):
            current_branch = branch.split()[-1]
            break
    return current_branch

def _main(dirs: List[str], args: argparse.Namespace) -> None:
    """
    Execute the main logic of the script

    :param dirs: Directories containing git repos
    :param args: Command line arguments
    """
    pad = _pad = "   "
    pad2 = _pad * 2
    for dir in dirs:
        if args.quiet:
            pad = f"{_pad}{dir}: "
            pad2 = f"{_pad}{_pad}{dir}: "
    
        if args.purge:
            logger.info(f"Purging ALL remote tracking branches from {dir}")
            
            proc = subprocess.check_output([shutil.which("git"), "--no-pager", "-C", dir, "branch",
                                            "--list", "-r", "origin/*", "--format", "%(refname:short)"])

            # trying to batch the delete without rate limiting will crash git on very large repos
            for branch in _parse_branches(proc):
                if branch == "origin":
                    continue
                if branch:
                    logger.debug(f"{pad}Deleting remote tracking branch: {branch}")
                    subprocess.check_output([shutil.which("git"), "-C", dir, "branch", "-r", "-D", branch])
            
        if args.no_fetch:
            logger.debug(f"Scanning {dir}")
        elif args.no_prune:
            logger.debug(f"Fetching {dir}")
            # not checking return code as errors are expected for non-repo folders
            proc = subprocess.run([shutil.which("git"), "-C", dir, "fetch"], capture_output=True)
        else:
            logger.debug(f"Fetching & pruning {dir}")
            # not checking return code as errors are expected for non-repo folders
            proc = subprocess.run([shutil.which("git"), "-C", dir, "fetch", "--prune"], capture_output=True)

        if not args.no_fetch:
            if proc.stderr.decode().startswith("fatal: not a git repository"):
                continue
        
        local_branches = _parse_branches(
            subprocess.check_output([shutil.which("git"), "--no-pager", "-C", dir, "branch", "--format", 
                                     "'%(refname:short) %(upstream:short) %(upstream:track)'"]))
        
        remote_branches = _parse_branches(subprocess.check_output([shutil.which("git"), "--no-pager", "-C", dir, 
                                                                  "branch", "--remote"]))
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
        
        current_branch = _find_current_branch(dir)

        if current_branch is None:
            logger.warning(f"{pad}{Colours.yellow}Unable to determine current branch{Colours.clear}")
        if root_branch is None:
            logger.warning(f"{pad}{Colours.yellow}Unable to determine root branch{Colours.clear}")
        if root_branch is None or current_branch is None:
            if args.ff:
                logger.warning(f"{pad}{Colours.yellow}--ff will be skipped{Colours.clear}")
            if args.delete:
                logger.warning(f"{pad}{Colours.yellow}--delete will be skipped{Colours.clear}")

        for branch in local_branches:
            branch_name = branch.split()[0].replace("'", "", 1)
            status = "[" + branch.split('[')[-1].replace("'", "")

            if "HEAD" in branch:
                logger.info(f"{pad}{Colours.yellow}{branch}{Colours.clear}")
            elif "origin" not in branch:
                logger.info(f"{pad}{Colours.yellow}{branch.rstrip()} [local only]{Colours.clear}")
            elif ("[ahead" in branch):
                logger.debug(f"{pad}{Colours.yellow}{branch_name} {status}")
            
            elif ("[behind" in branch):
                if args.ff and branch_name == root_branch:
                    logger.info(f"{pad}{Colours.yellow}{branch_name} {status}{Colours.clear}")
                    logger.info(f"{pad2}Fast-forwarding {branch_name}")

                    if current_branch == root_branch:
                        ff_result = subprocess.run([shutil.which("git"), "-C", dir, "pull", "--ff-only"], 
                                                    capture_output=True)
                    else:
                        # equivalent to a pull -ff-only (only works on non-current branch)
                        ff_result = subprocess.run(
                            [shutil.which("git"), "-C", dir, "fetch", "origin", f"{root_branch}:{root_branch}"], 
                            capture_output=True)
                        
                    if ff_result.returncode != 0:
                        logger.error(f"{pad2}{Colours.red}Unable to fast-forward {branch_name}{Colours.clear}")
                        logger.error(f"{pad2}{Colours.red}{ff_result.stderr.decode()}{Colours.clear}")
                else:
                    logger.debug(f"{pad}{Colours.yellow}{branch_name} {status}{Colours.clear}")

            elif "[gone]" in branch:
                logger.info(f"{pad}{Colours.red}{branch_name} [remote deleted]{Colours.clear}")
                if args.delete:
                    safe_to_delete = True
                    if current_branch == branch_name:
                        git_status = subprocess.run([shutil.which("git"), "-C", dir, "status", "--porcelain"],
                                                     capture_output=True)
                        if git_status.stdout.decode():
                            safe_to_delete = False
                            logger.warning(f"{pad2}{Colours.yellow}Switching precluded by uncommitted changes on "
                                           f"current branch - skipping delete of {branch_name}{Colours.clear}")
                        else:
                            logger.debug(f"{pad2}Switching from {current_branch} to {root_branch}")
                            switch_result = subprocess.run([shutil.which("git"), "-C", dir, "switch", root_branch],
                                                        capture_output=True)
                            
                            if switch_result.returncode != 0:
                                safe_to_delete = False
                                logger.error(f"{pad2}{Colours.red}Switch failed, skipping delete of "
                                             f"{branch_name}{Colours.clear}")
                                logger.error(f"{pad}{Colours.red}{switch_result.stderr.decode()}{Colours.clear}")
                            else:
                                current_branch = root_branch

                    if safe_to_delete:
                        logger.info(f"{pad2}Deleting local branch {branch_name}")
                        del_result = subprocess.run([shutil.which("git"), "-C", dir, "branch", "-D", branch_name],
                                                    capture_output=True)
                        if del_result.returncode != 0:
                            logger.error(f"{pad}{Colours.red}Unable to delete {branch_name}{Colours.clear}")
                            logger.error(f"{pad}{Colours.red}{ff_result.stderr.decode()}{Colours.clear}")
            else:
                logger.debug(f"{pad}{Colours.green}{branch_name} [up to date]{Colours.clear}")
        
        if args.remote:
            for remote_branch in remote_branches:
                if "/HEAD" in remote_branch:
                    continue 
                basename = remote_branch.split("origin/")[-1]
                if basename not in [b.split()[0].rstrip().replace("'", "", 1) for b in local_branches]:
                    logger.info(f"{pad}{Colours.yellow}{basename} [remote only]{Colours.clear}")
               
if __name__ == "__main__":
    parser = argparse.ArgumentParser("Recursively scan (optionally fetching & pruning) all git repos and display their status compared to their remote tracking branches.")
    parser.add_argument("--directory", type=str, help="(Optional) Name of the directory to process [Default: 'D:\dev' (Windows) or '~' (Linux)]")
    parser.add_argument("--depth", default=3, type=int, help="(Optional) Search depth for directories to process [Default: 3]")
    parser.add_argument("--quiet", action="store_true", help="(Optional) Display local/gone branches only [Default: output all operations + branch status]")
    parser.add_argument("--no-fetch", action="store_true", help="(Optional) Skip fetching of remote tracking branches [Default: fetch branches]")
    parser.add_argument("--no-prune", action="store_true", help="(Optional) Skip pruning of remote tracking branches [Default: prune branches]")
    parser.add_argument("--include", action="append", default=[], required=False, help="(Optional) Only include directories matching sub-string (pass once per directory name to include multiple) [Default: no exclusions]")
    parser.add_argument("--exclude", action="append", default=[], required=False, help="(Optional) Skip processing of directory matching sub-string (pass once per directory name to exclude multiple) [Default: no exclusions]")
    parser.add_argument("--remote", action="store_true", help="(Optional) Report remote only branches (based on remote tracking branches/fetch rules) [Default: Not reported]")
    parser.add_argument("--purge", action="store_true", help="(Optional) Delete ALL remote tracking branches [Default: Only pruned if remote branch has been deleted]")
    parser.add_argument("--ff", action="store_true", help="(Optional) Fast-forward master/main branch after fetch [Default: fetch only]")
    parser.add_argument("--delete", action="store_true", help="(Optional) Delete orphaned local branches [Default: report only]")
    args = parser.parse_args()

    if not args.directory:
        if sys.platform == "linux":
            args.directory = "~"
        else:
            args.directory = r"D:\dev"

    if args.quiet:
        for handler in logger.handlers:
            if type(handler) is logging.StreamHandler:
                handler.setLevel(logging.INFO)

    _main(_get_dirs_with_depth(os.path.expanduser(args.directory), args.depth, args.include, args.exclude), args)