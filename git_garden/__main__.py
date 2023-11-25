import os
import sys
import argparse
import logging

from . import CustomFormatter, GitGarden

logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)
logger.addHandler(
    logging.StreamHandler()
)  # must be defined before file_handler to avoid formatting clash

file_handler = logging.FileHandler(
    os.path.join(os.path.dirname(__file__), "garden.log"), mode="w"
)
custom_fmtr = CustomFormatter(
    fmt="{asctime} - {name} - {levelname:^5s} - {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
)
file_handler.setFormatter(custom_fmtr)
logger.addHandler(file_handler)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Recursively scan (optionally fetching & pruning) all git repos and display"
        " their status compared to their remote tracking branches.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--directory",
        type=str,
        help="(Optional) Name of the directory to process "
        "[Default: 'D:\dev' (Windows) or '~' (Linux)]",
    )
    parser.add_argument(
        "--depth",
        default=3,
        type=int,
        help="(Optional) Search depth for directories to process" " [Default: 3]",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="(Optional) Display local/gone branches only"
        " [Default: output all operations + branch status]",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="(Optional) Skip fetching of remote tracking branches"
        " [Default: fetch branches]",
    )
    parser.add_argument(
        "--no-prune",
        action="store_true",
        help="(Optional) Skip pruning of remote tracking branches"
        " [Default: prune branches]",
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
        help="(Optional) Delete ALL remote tracking branches"
        " [Default: Only pruned if remote branch has been deleted]",
    )
    parser.add_argument(
        "--ff",
        action="store_true",
        help="(Optional) Fast-forward master/main branch after fetch"
        " [Default: fetch only]",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="(Optional) Delete orphaned local branches" " [Default: report only]",
    )
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

    GitGarden(logger, args)
