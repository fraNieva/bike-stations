"""
Alembic environment configuration.

Reads the DATABASE_URL from environment variables so migrations can run
in any environment (local Docker, Railway, CI) without hardcoded credentials.
Imports all models so Alembic can detect schema changes automatically
when using --autogenerate.
"""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

load_dotenv()

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Override sqlalchemy.url with the environment variable
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base and all models so Alembic can detect changes
from app.database import Base
import app.models  # noqa: F401 — registers all models with Base.metadata

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in offline mode (no live DB connection needed).

    Generates SQL scripts that can be reviewed and applied manually.
    Useful for auditing changes before applying them to production.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in online mode (connects directly to the database).

    Used in normal operation — Railway runs this automatically
    before starting the application server.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()