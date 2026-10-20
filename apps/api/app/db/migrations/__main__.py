"""Keep the migration command executable until Alembic arrives in TASK-004."""

import logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Report the empty migration state without pretending to alter a database."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger.info("No migrations yet; Alembic will be configured in TASK-004.")


if __name__ == "__main__":
    main()
