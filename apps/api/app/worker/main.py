"""Worker process placeholder; handlers are introduced with the outbox foundation."""

import logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Expose a valid process entry point without starting an unimplemented loop."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger.info("Worker foundation ready; processing loop is not enabled yet.")


if __name__ == "__main__":
    main()
