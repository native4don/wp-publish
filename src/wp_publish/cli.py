"""Command line: wp-publish PAGES_YML --credentials FILE [--publish]."""
import argparse
import sys
from pathlib import Path

from .config import ConfigError
from .credentials import CredentialError
from .publish import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wp-publish",
        description="Publish the pages listed in pages.yml to WordPress. A dry run unless --publish is given.",
    )
    parser.add_argument("pages", type=Path, help="the pages.yml beside the documents")
    parser.add_argument("--credentials", type=Path, required=True, help="the credential file (mode 600)")
    parser.add_argument("--publish", action="store_true", help="send the pages; without it nothing is sent")
    args = parser.parse_args(argv)
    try:
        return run(args.pages, args.credentials, publish=args.publish)
    except (ConfigError, CredentialError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
