"""The voice transport: a FastAPI backend that owns the Gnani key and runs the call's audio loop."""

from samajh.server.app import create_app

__all__ = ["create_app"]
