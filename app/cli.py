# app/cli.py  (or add to app/main.py if you prefer)
from __future__ import annotations

import uvicorn


def run_dev():
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8033,
        reload=True,
    )
