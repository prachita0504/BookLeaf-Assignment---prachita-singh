"""Logging setup: one consistent format for app, uvicorn and AI-call logs."""

import logging


def setup_logging(debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    # The Mongo driver is very chatty at DEBUG level.
    logging.getLogger("pymongo").setLevel(logging.WARNING)
