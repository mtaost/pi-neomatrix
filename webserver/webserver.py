"""Backward-compatible entry point for the display web service."""

from webserver.app import create_app

__all__ = ["create_app"]
