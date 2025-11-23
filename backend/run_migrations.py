"""
Run database migrations on application startup.

This script runs Alembic migrations programmatically, which is needed for
Railway deployment where we don't have shell access to run `alembic upgrade`.
"""
import sys
import logging
from pathlib import Path
from alembic import command
from alembic.config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run all pending database migrations."""
    try:
        logger.info("Starting database migrations...")

        # Get the directory containing this script
        backend_dir = Path(__file__).parent

        # Create Alembic config
        alembic_ini = backend_dir / "alembic.ini"

        if not alembic_ini.exists():
            logger.error(f"Alembic config not found: {alembic_ini}")
            sys.exit(1)

        # Load Alembic configuration
        alembic_cfg = Config(str(alembic_ini))

        # Set the script location (where migrations are stored)
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

        # Run migrations to head (latest version)
        logger.info("Running migrations to head...")
        command.upgrade(alembic_cfg, "head")

        logger.info("✓ Database migrations completed successfully")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


def check_current_revision():
    """Check the current database revision."""
    try:
        backend_dir = Path(__file__).parent
        alembic_ini = backend_dir / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini))
        alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

        from alembic.runtime.migration import MigrationContext
        from database import engine

        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()

            if current_rev:
                logger.info(f"Current database revision: {current_rev}")
            else:
                logger.info("Database has no migration history yet")

            return current_rev

    except Exception as e:
        logger.warning(f"Could not check current revision: {e}")
        return None


if __name__ == "__main__":
    # Allow checking current revision with --check flag
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_current_revision()
    else:
        success = run_migrations()
        sys.exit(0 if success else 1)
