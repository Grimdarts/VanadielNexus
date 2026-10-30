"""Where the app lives, where bundled resources are, and where player data goes."""
import os
import sys

APP_NAME = "VanadielNexus"
IS_FROZEN = getattr(sys, "frozen", False)


def app_dir() -> str:
    """Folder holding the exe (frozen) or the repository root (running from source)."""
    if IS_FROZEN:
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(*parts: str) -> str:
    """Path to a file shipped inside the app (vanadiel_nexus/resources)."""
    if IS_FROZEN:
        base = os.path.join(getattr(sys, "_MEIPASS", app_dir()), "vanadiel_nexus", "resources")
    else:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
    return os.path.join(base, *parts)


def _is_writable(folder: str) -> bool:
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, ".write-test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def data_dir() -> str:
    """Player data sits next to the app (portable, matches v1); %APPDATA% if that folder is read-only.
    VN_DATA_DIR overrides both (tests and screenshots use a throwaway copy)."""
    override = os.environ.get("VN_DATA_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    portable = os.path.join(app_dir(), "data")
    if _is_writable(portable):
        return portable
    fallback = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
    os.makedirs(fallback, exist_ok=True)
    return fallback
