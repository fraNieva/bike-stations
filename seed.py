"""
Seed script — creates the initial admin user and optionally the first device.

Run this once after the first deployment to set up the system.
The person running it chooses their own credentials.

Usage:
    docker-compose exec app python seed.py      # interactive (recommended)
    docker-compose exec app python seed.py --no-device   # user only, no device

Environment:
    DATABASE_URL must be set (set automatically inside Docker).
"""

import argparse
import os
import sys

import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_secret(secret: str) -> str:
    """Return a bcrypt hash of the given secret."""
    return bcrypt.hashpw(secret.encode(), bcrypt.gensalt()).decode()


def get_engine():
    """Create a SQLAlchemy engine from DATABASE_URL."""
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)
    return create_engine(url)


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_user(session: Session, email: str, password: str) -> bool:
    """
    Insert the first user if it does not already exist.

    Returns True if created, False if it already existed.
    """
    row = session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).fetchone()

    if row:
        print(f"  [skip] User '{email}' already exists (id={row.id}).")
        return False

    password_hash = hash_secret(password)
    session.execute(
        text(
            "INSERT INTO users (email, password_hash, is_active) "
            "VALUES (:email, :password_hash, true)"
        ),
        {"email": email, "password_hash": password_hash},
    )
    session.commit()
    print(f"  [ok]   User '{email}' created.")
    return True


def seed_device(session: Session, station_id: str, api_key: str) -> bool:
    """
    Register a device if the station_id does not already exist.

    Returns True if created, False if it already existed.
    """
    row = session.execute(
        text("SELECT id FROM devices WHERE station_id = :station_id"),
        {"station_id": station_id},
    ).fetchone()

    if row:
        print(f"  [skip] Device '{station_id}' already registered (id={row.id}).")
        return False

    api_key_hash = hash_secret(api_key)
    session.execute(
        text(
            "INSERT INTO devices (station_id, api_key_hash, is_active) "
            "VALUES (:station_id, :api_key_hash, true)"
        ),
        {"station_id": station_id, "api_key_hash": api_key_hash},
    )
    session.commit()
    print(f"  [ok]   Device '{station_id}' registered.")
    return True


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def prompt(label: str, secret: bool = False) -> str:
    """Prompt the user for input. Hides input if secret=True."""
    import getpass

    if secret:
        return getpass.getpass(f"{label}: ")
    return input(f"{label}: ").strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Seed the database with the first admin user.")
    parser.add_argument("--no-device", action="store_true", help="Skip device registration")
    return parser.parse_args()


def main() -> None:
    """Entry point — prompt for credentials interactively, then seed the database."""
    args = parse_args()

    print("\n=== Bike Stations — Initial Setup ===\n")

    # --- User ---
    print("Create the first admin user:")
    email = prompt("  Email")
    password = prompt("  Password", secret=True)
    password_confirm = prompt("  Confirm password", secret=True)

    if not email or not password:
        print("\nERROR: Email and password are required.")
        sys.exit(1)

    if password != password_confirm:
        print("\nERROR: Passwords do not match.")
        sys.exit(1)

    # --- Device ---
    create_device = False
    station_id = ""
    api_key = ""

    if not args.no_device:
        print("\nRegister first device? (leave Station ID blank to skip)")
        station_id = prompt("  Station ID")
        if station_id:
            api_key = prompt("  API key (min 32 chars)", secret=True)
            if len(api_key) < 32:
                print("\nERROR: API key must be at least 32 characters.")
                sys.exit(1)
            create_device = True

    # --- Run ---
    print("\nSetting up...")
    engine = get_engine()
    with Session(engine) as session:
        seed_user(session, email, password)
        if create_device:
            seed_device(session, station_id, api_key)

    print("\nDone.\n")


if __name__ == "__main__":
    main()