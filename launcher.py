"""
launcher.py — Entry point for the PyInstaller-bundled KSEI Dashboard .exe.

When frozen (running as exe):
  - sys._MEIPASS  → the _internal/ folder (read-only bundled files)
  - sys.executable → the .exe itself (data stored next to it)

When running as plain script:
  - behaves the same as running: py -m streamlit run app.py
"""
import os
import socket
import sys
import threading
import time
import webbrowser


def _get_app_dir() -> str:
    """Directory that contains app.py (and other bundled .py files)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS          # _internal/ when --onedir
    return os.path.dirname(os.path.abspath(__file__))


def _get_data_dir() -> str:
    """Directory for persistent data (ksei.db).  Writable, survives upgrades."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)   # beside the .exe
    return os.path.dirname(os.path.abspath(__file__))


def _free_port(preferred: int = 8501) -> int:
    """Return preferred port if available, else any free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", preferred)) != 0:
            return preferred          # preferred is free
    # Fall back to any free port
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _open_browser(port: int, delay: float = 5.0) -> None:
    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    app_dir  = _get_app_dir()
    data_dir = _get_data_dir()
    app_path = os.path.join(app_dir, "app.py")
    port     = _free_port(8501)

    # Tell db.py where to store ksei.db
    os.environ["KSEI_DATA_DIR"] = data_dir

    # ── Streamlit configuration via env-vars ──────────────────────────────
    # CRITICAL: when PyInstaller freezes Streamlit it looks like a "source
    # install", causing Streamlit to set developmentMode=True which blocks
    # the --server.port flag.  Force it off explicitly.
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"]    = "false"
    os.environ["STREAMLIT_SERVER_PORT"]                = str(port)
    os.environ["STREAMLIT_SERVER_HEADLESS"]            = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"]   = "none"
    os.environ["STREAMLIT_RUNNER_FAST_RERUNS"]         = "false"

    # Open browser in background after Streamlit is ready
    threading.Thread(
        target=_open_browser, args=(port,), daemon=True
    ).start()

    # Hand off to Streamlit CLI
    # Pass port via env-var (above) so it still works even if dev-mode
    # detection misfiles; also pass as flag for belt-and-suspenders.
    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit", "run", app_path,
        "--global.developmentMode=false",
        f"--server.port={port}",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
