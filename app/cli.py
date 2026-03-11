# app/cli.py  (or add to app/main.py if you prefer)
import uvicorn


def run_dev():
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
    )
