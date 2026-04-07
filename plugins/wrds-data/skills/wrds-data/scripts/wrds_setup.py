#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["wrds"]
# ///
"""
Check WRDS environment and guide credential setup.

Usage:
    uv run python wrds_setup.py [--check | --setup]

Actions:
    --check   (default) Report whether wrds package and .pgpass are configured.
    --setup   Interactive: prompt for WRDS username/password and write ~/.pgpass.
"""

import argparse
import os
import platform
import stat
import sys
from pathlib import Path


WRDS_HOST = "wrds-pgdata.wharton.upenn.edu"
WRDS_PORT = "9737"
WRDS_DB = "wrds"


def _pgpass_path() -> Path:
    if platform.system() == "Windows":
        return Path(os.environ.get("APPDATA", "")) / "postgresql" / "pgpass.conf"
    return Path.home() / ".pgpass"


def _pgpass_has_wrds(pgpass: Path) -> bool:
    """Return True if .pgpass already contains a WRDS entry."""
    if not pgpass.exists():
        return False
    text = pgpass.read_text()
    return WRDS_HOST in text


def _check() -> dict:
    """Return a status dict with booleans for each prerequisite."""
    result = {}

    # 1. Check wrds package
    try:
        import wrds  # noqa: F401
        result["wrds_installed"] = True
    except ImportError:
        result["wrds_installed"] = False

    # 2. Check .pgpass
    pgpass = _pgpass_path()
    result["pgpass_exists"] = pgpass.exists()
    result["pgpass_has_wrds"] = _pgpass_has_wrds(pgpass)

    # 3. Check file permissions (Unix only)
    if pgpass.exists() and platform.system() != "Windows":
        mode = pgpass.stat().st_mode
        result["pgpass_permissions_ok"] = (mode & 0o077) == 0  # no group/other access
    else:
        result["pgpass_permissions_ok"] = None

    # 4. Try a test connection (quick)
    if result["wrds_installed"] and result["pgpass_has_wrds"]:
        try:
            import wrds
            db = wrds.Connection(autoconnect=True)
            db.close()
            result["connection_ok"] = True
        except Exception as e:
            result["connection_ok"] = False
            result["connection_error"] = str(e)
    else:
        result["connection_ok"] = None

    return result


def _print_status(status: dict) -> None:
    def icon(val):
        if val is True:
            return "OK"
        elif val is False:
            return "MISSING"
        return "SKIPPED"

    print("=== WRDS Setup Status ===")
    print(f"  wrds package installed : {icon(status['wrds_installed'])}")
    print(f"  .pgpass file exists    : {icon(status['pgpass_exists'])}")
    print(f"  .pgpass has WRDS entry : {icon(status['pgpass_has_wrds'])}")
    if status["pgpass_permissions_ok"] is not None:
        print(f"  .pgpass permissions    : {icon(status['pgpass_permissions_ok'])}")
    if status["connection_ok"] is True:
        print(f"  Test connection        : {icon(status['connection_ok'])}")
    elif status["connection_ok"] is False:
        print(f"  Test connection        : FAILED — {status.get('connection_error', 'unknown')}")

    if all(status.get(k) for k in ("wrds_installed", "pgpass_has_wrds", "connection_ok")):
        print("\nAll checks passed. WRDS is ready to use.")
    else:
        print("\nSome checks failed. Run with --setup to configure credentials.")
        if not status["wrds_installed"]:
            print("  Hint: install wrds with  uv pip install wrds")
        if not status["pgpass_has_wrds"]:
            print(f"  Hint: run this script with --setup, or manually add a line to {_pgpass_path()}:")
            print(f"        {WRDS_HOST}:{WRDS_PORT}:{WRDS_DB}:YOUR_USERNAME:YOUR_PASSWORD")
            print("  Get your WRDS account at https://wrds-www.wharton.upenn.edu/register/")


def _setup() -> None:
    """Interactively create or update .pgpass with WRDS credentials."""
    pgpass = _pgpass_path()

    if _pgpass_has_wrds(pgpass):
        print(f"WRDS entry already exists in {pgpass}.")
        resp = input("Overwrite? [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            return

    username = input("WRDS username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    import getpass
    password = getpass.getpass("WRDS password: ")
    if not password:
        print("Password cannot be empty.")
        sys.exit(1)

    entry = f"{WRDS_HOST}:{WRDS_PORT}:{WRDS_DB}:{username}:{password}\n"

    # Read existing content, remove old WRDS lines
    existing = ""
    if pgpass.exists():
        existing = pgpass.read_text()
        lines = [l for l in existing.splitlines(keepends=True) if WRDS_HOST not in l]
        existing = "".join(lines)

    pgpass.parent.mkdir(parents=True, exist_ok=True)
    pgpass.write_text(existing + entry)

    # Fix permissions on Unix
    if platform.system() != "Windows":
        pgpass.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600

    print(f"WRDS credentials written to {pgpass}")

    # Verify
    try:
        import wrds
        db = wrds.Connection(autoconnect=True)
        db.close()
        print("Connection test: OK")
    except Exception as e:
        print(f"Connection test: FAILED — {e}")
        print("Check your username/password and try again.")


def main():
    parser = argparse.ArgumentParser(description="WRDS setup helper")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", default=True, help="Check setup status (default)")
    group.add_argument("--setup", action="store_true", help="Interactive credential setup")
    args = parser.parse_args()

    if args.setup:
        _setup()
    else:
        status = _check()
        _print_status(status)


if __name__ == "__main__":
    main()
