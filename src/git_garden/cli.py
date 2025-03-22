import os
import argparse
import logging
from git_garden import GitGarden, Colours
from typing import Optional, Literal


class CustomFormatter(logging.Formatter):
    """
    This formatter extends the base logging.Formatter and provides a method for custom parsing of log messages before
    they are emitted.

    :param fmt: The format string for the log message.
    :param datefmt: The format string for the date in the log message.
    :param style: The formatting style).
    """

    def __init__(
        self,
        fmt: str,
        datefmt: Optional[str] = None,
        style: Literal["%", "{", "$"] = "{",
    ) -> None:
        super().__init__(fmt, datefmt, style)
        self.colours = Colours()

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
        message = message.replace(self.colours.yellow, "").replace(self.colours.red, "").replace(self.colours.green, "")
        message = message.replace(self.colours.clear, "")
        return message


logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()  # must be defined before file_handler to avoid formatting clash
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

file_handler = logging.FileHandler(os.path.join(os.path.dirname(__file__), "garden.log"), mode="w")
custom_fmtr = CustomFormatter(
    fmt="{asctime} - {name} - {levelname:^5s} - {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
)
file_handler.setFormatter(custom_fmtr)
logger.addHandler(file_handler)


# preserve undecorated entry point for tests and module use
def main() -> None:
    """
    Main entry point after `click` or module `__main__` call.
    `argparse` will extract cli args from `sys.argv`.
    """
    parser = argparse.ArgumentParser(
        "Recursively scan (optionally fetching & pruning) all git repos and display"
        " their status compared to their remote tracking branches.\n",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--dir",
        default=os.getcwd(),
        type=str,
        help="(Optional) Name of the directory to process [Default: current working directory]",
    )
    parser.add_argument(
        "--depth",
        default=3,
        type=int,
        help="(Optional) Search depth for directories to process [Default: 3]",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="(Optional) Skip fetching of remote tracking branches [Default: fetch branches]",
    )
    parser.add_argument(
        "--no-prune",
        action="store_true",
        help="(Optional) Skip pruning of remote tracking branches [Default: prune branches]",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        required=False,
        help="(Optional) Only include"
        " directories matching sub-string (pass once per directory name to include multiple) "
        " [Default: no exclusions]",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        required=False,
        help="(Optional) Skip processing of"
        " directory matching sub-string (pass once per directory name to exclude multiple)"
        " [Default: no exclusions]",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="(Optional) Report remote only branches"
        " (based on remote tracking branches/fetch rules) [Default: Not reported]",
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="(Optional) Delete ALL remote tracking branches [Default: Only pruned if remote branch has been deleted]",
    )
    parser.add_argument(
        "--ff",
        action="store_true",
        help="(Optional) Fast-forward main/master branch after fetch [Default: fetch only]",
    )
    parser.add_argument(
        "--ff-all",
        action="store_true",
        help="(Optional) Fast-forward all local branches [Default: fetch only]",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="(Optional) Delete orphaned local branches [Default: report only]",
    )
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        required=False,
        help="(Optional) A non-default branch name to treat as root instead of main/master"
        " (--root can be passed multiples times) [Default: main/master]",
    )
    args = parser.parse_args()

    gg = GitGarden(logger, args)
    gg.main(gg.get_dirs_with_depth(gg.args.dir, gg.args.depth))
