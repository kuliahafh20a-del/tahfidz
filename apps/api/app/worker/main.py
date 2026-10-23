"""Background worker for private media validation."""

import asyncio
import logging

from app.core.config import get_settings
from app.db.session import close_database, get_database
from app.modules.media.service import MediaValidationWorker
from app.modules.media.storage import S3ObjectStorage

logger = logging.getLogger(__name__)


async def run() -> None:
    """Continuously validate completed uploads with safe retry behavior."""
    settings = get_settings()
    database = get_database()
    storage = S3ObjectStorage(settings)
    try:
        while True:
            processed = False
            try:
                async with database.session_factory() as session:
                    processed = await MediaValidationWorker(session, storage, settings).run_once()
            except Exception:
                logger.error("Media validation cycle failed; retrying without logging payload data")
            if not processed:
                await asyncio.sleep(settings.media_worker_poll_seconds)
    finally:
        await close_database()


def main() -> None:
    """Start the worker process."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(run())


if __name__ == "__main__":
    main()
