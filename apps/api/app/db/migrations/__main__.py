"""Command-line entry point for reproducible Alembic migrations."""

import argparse
from collections.abc import Sequence

from alembic import command

from app.db.migrations.runner import build_alembic_config


def parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the intentionally small migration command surface."""
    parser = argparse.ArgumentParser(description="Manage YAQin database migrations")
    parser.add_argument(
        "action",
        nargs="?",
        default="upgrade",
        choices=("upgrade", "downgrade", "current", "check"),
    )
    parser.add_argument("revision", nargs="?", default=None)
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> None:
    """Run an Alembic action; a bare command upgrades to the latest revision."""
    args = parse_args(arguments)
    configuration = build_alembic_config()

    if args.action == "upgrade":
        command.upgrade(configuration, args.revision or "head")
    elif args.action == "downgrade":
        command.downgrade(configuration, args.revision or "-1")
    elif args.action == "current":
        command.current(configuration, verbose=True)
    else:
        command.check(configuration)


if __name__ == "__main__":
    main()
