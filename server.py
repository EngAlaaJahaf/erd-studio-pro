"""TESTR ERD Studio Pro — Application Runner.

Entry point to launch the FastAPI server via Uvicorn.
Usage:
    python server.py
"""
import sys
import uvicorn
from app.config import SERVER_HOST, SERVER_PORT


def main():
    host = SERVER_HOST
    port = SERVER_PORT
    # Allow command line overrides e.g. python server.py 8600 or python server.py 127.0.0.1 8600
    if len(sys.argv) == 2:
        try:
            port = int(sys.argv[1])
        except ValueError:
            host = sys.argv[1]
    elif len(sys.argv) >= 3:
        host = sys.argv[1]
        try:
            port = int(sys.argv[2])
        except ValueError:
            pass

    print(f"🚀 Starting TESTR ERD Studio Pro on http://{host}:{port} ...")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
