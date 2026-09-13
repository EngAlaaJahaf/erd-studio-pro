"""TESTR ERD Studio Pro — application package.

This is the installable package for the standalone ERD Studio server.
Run `pip install -e .` at the repository root to install it in editable mode,
then start the server anywhere with::

    python server.py          # or uvicorn app.main:app

Package layout:

- ``app.main``        : FastAPI application factory (create_app) + ASGI entry point
- ``app.config``      : typed settings via pydantic-settings (reads .env)
- ``app.logging_conf``: shared logging configuration
- ``app.exceptions``  : domain exceptions + FastAPI exception handlers
- ``app.core``        : database access layer (SQLite, schema cache, presets)
- ``app.connectors``  : DBMS connectors (Oracle sync, SQLite file, etc.)
- ``app.services``    : business logic (SQL/Data-Dictionary import/export, diagrams)
- ``app.ai``          : AI assistant / classification / LLM diagram generation
- ``app.api``         : REST routes, grouped by feature
"""

__version__ = "1.1.0"
__title__ = "TESTR ERD Studio Pro"
