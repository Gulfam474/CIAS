"""Launch CIAS as a desktop window."""

import threading
import time
import webview

from app import app


def _serve():
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    time.sleep(0.8)
    webview.create_window(
        "CIAS — Classroom Information and Availability System",
        "http://127.0.0.1:5000",
        width=1380,
        height=860,
        min_size=(1100, 700),
    )
    webview.start()
