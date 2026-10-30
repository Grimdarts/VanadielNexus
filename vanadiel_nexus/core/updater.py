"""Self-update from GitHub Releases. Only the exe is replaced; data/ is never touched."""
import json
import os
import re
import shutil
import subprocess
import urllib.request

GITHUB_REPO = "Grimdarts/VanadielNexus"
ASSET_NAME = "vanadielnexus.exe"
MIN_EXE_BYTES = 1_000_000


def version_tuple(ver: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", ver or "")[:3]) or (0,)


def is_newer(latest: str, current: str) -> bool:
    return version_tuple(latest) > version_tuple(current)


def pick_asset(release: dict):
    return next((a for a in release.get("assets", []) if a.get("name", "").lower() == ASSET_NAME), None)


def fetch_latest_release(timeout: float = 10) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "VanadielNexus"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def check(current_version: str):
    """Returns {'version', 'url', 'notes'} when a newer release with an exe exists, else None."""
    release = fetch_latest_release()
    latest = release.get("tag_name", "").lstrip("vV")
    asset = pick_asset(release)
    if asset and is_newer(latest, current_version):
        return {"version": latest, "url": asset["browser_download_url"], "notes": release.get("body") or ""}
    return None


def swap_script(new_path: str, exe_path: str) -> str:
    """Windows can't overwrite a running exe: this waits for the app to exit, swaps, and relaunches."""
    return (
        "@echo off\r\n"
        "set n=0\r\n"
        ":retry\r\n"
        f'move /Y "{new_path}" "{exe_path}" >nul 2>&1 && goto done\r\n'
        "set /a n+=1\r\n"
        "if %n% geq 60 goto done\r\n"
        "timeout /t 1 /nobreak >nul\r\n"
        "goto retry\r\n"
        ":done\r\n"
        f'start "" "{exe_path}"\r\n'
        'del "%~f0"\r\n'
    )


def download_and_stage(url: str, exe_path: str) -> str:
    """Downloads the new exe next to the current one and writes the swap script. Returns the script path."""
    new_path = exe_path + ".new"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VanadielNexus"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(new_path, "wb") as out:
            shutil.copyfileobj(resp, out)
        if os.path.getsize(new_path) < MIN_EXE_BYTES:
            raise RuntimeError("Downloaded file is too small; update cancelled.")
    except Exception:
        if os.path.exists(new_path):
            os.remove(new_path)
        raise
    cmd_path = os.path.join(os.path.dirname(exe_path), "_vn_update.cmd")
    with open(cmd_path, "w", encoding="utf-8") as f:
        f.write(swap_script(new_path, exe_path))
    return cmd_path


def launch_swap(cmd_path: str) -> None:
    subprocess.Popen(
        ["cmd", "/c", cmd_path],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
