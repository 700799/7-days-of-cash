"""Vercel serverless entrypoint.

Vercel's ``@vercel/python`` builder expects an importable ASGI app named ``app``
(or a ``handler`` callable). Pointing ``vercel.json`` at this module keeps the
FastAPI app surface centralized in ``api.main``.
"""
from .main import app  # noqa: F401
