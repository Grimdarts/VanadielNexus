"""Check installed addons against their source on GitHub and update them safely.

How a check works (one GitHub API call per source repository, not per addon):
    1. Fetch the repository's file tree. Every file comes with its git blob hash.
    2. Hash the local copy of each file the same way git does.
    3. Any file that's missing or different means an update is available.

Official Windower addons come from github.com/Windower/Lua (addons/<Name>/). Third-party addons
can be given a source such as "owner/repo", "owner/repo/sub/folder" or a GitHub folder URL.
Updating backs up the addon folder first, never touches its data/ folder (saved settings), and
checks every downloaded file against the hash GitHub reported before writing it.
"""
import hashlib
import json
import os
import re
import time
import urllib.request
import zipfile

OFFICIAL = {"owner": "Windower", "repo": "Lua", "path": "addons", "branch": ""}
OFFICIAL_BRANCHES = ("dev",)  # what the Windower launcher installs (local copies match dev, not live)
SKIP_DIRS = {"data"}


def blob_sha(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def parse_source(text: str):
    """'owner/repo[/path][@branch]' or a github.com URL -> {owner, repo, path, branch}; None if unusable."""
    t = (text or "").strip()
    m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s#?]+)(?:/tree/([^/\s]+)(?:/(.*))?)?/?$", t)
    if m:
        owner, repo, branch, path = m.group(1), m.group(2), m.group(3) or "", m.group(4) or ""
    else:
        m = re.match(r"^([\w.-]+)/([\w.-]+)((?:/[^@\s]+)*)(?:@([\w./-]+))?$", t)
        if not m:
            return None
        owner, repo, path, branch = m.group(1), m.group(2), (m.group(3) or "").strip("/"), m.group(4) or ""
    repo = repo.removesuffix(".git")
    return {"owner": owner, "repo": repo, "path": path.strip("/"), "branch": branch}


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "VanadielNexus"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "VanadielNexus"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_tree(owner: str, repo: str, branches=(), get_json=_get_json):
    """Returns (branch, {path: sha}) for the first branch that exists (repo default if none given)."""
    if not branches:
        branches = (get_json(f"https://api.github.com/repos/{owner}/{repo}")["default_branch"],)
    last_error = None
    for branch in branches:
        try:
            tree = get_json(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        except Exception as e:  # 404 for a missing branch; try the next one
            last_error = e
            continue
        return branch, {e["path"]: e["sha"] for e in tree.get("tree", []) if e.get("type") == "blob"}
    raise last_error or RuntimeError("No branch found")


def _remote_files(tree: dict, prefix: str) -> dict:
    """{path relative to the addon folder: sha} for one addon, data/ excluded."""
    base = prefix.strip("/") + "/" if prefix.strip("/") else ""
    files = {}
    for path, sha in tree.items():
        if base and not path.startswith(base):
            continue
        rel = path[len(base):]
        if rel.split("/", 1)[0].lower() in SKIP_DIRS:
            continue
        files[rel] = sha
    return files


def compare(local_folder: str, remote: dict) -> list:
    """Relative paths that are missing locally or differ from the source."""
    changed = []
    for rel, sha in remote.items():
        local = os.path.join(local_folder, *rel.split("/"))
        if not os.path.isfile(local) or blob_sha(local) != sha:
            changed.append(rel)
    return sorted(changed)


def _official_prefix(tree: dict, name: str):
    """Official addon folders keep their own capitalisation (e.g. addons/GearSwap)."""
    wanted = name.lower()
    for path in tree:
        parts = path.split("/")
        if len(parts) > 2 and parts[0] == "addons" and parts[1].lower() == wanted:
            return f"addons/{parts[1]}"
    return None


def scan(addons: list, sources: dict, get_json=_get_json) -> dict:
    """{addon name: result} where result has status, changed files and where the update comes from.

    status: 'up_to_date' | 'update_available' | 'no_source' | 'error'
    """
    trees, results = {}, {}

    def tree_for(src):
        key = (src["owner"], src["repo"], src["branch"])
        if key not in trees:
            branches = (src["branch"],) if src["branch"] else (
                OFFICIAL_BRANCHES if (src["owner"], src["repo"]) == ("Windower", "Lua") else ())
            trees[key] = fetch_tree(src["owner"], src["repo"], branches, get_json)
        return trees[key]

    for addon in addons:
        name = addon["name"]
        try:
            custom = parse_source(sources.get(name.lower(), ""))
            if custom:
                branch, tree = tree_for(custom)
                prefix = custom["path"]
                src = {**custom, "branch": branch}
            else:
                branch, tree = tree_for(OFFICIAL)
                prefix = _official_prefix(tree, name)
                if prefix is None:
                    results[name] = {"status": "no_source", "changed": []}
                    continue
                src = {**OFFICIAL, "branch": branch}
            remote = _remote_files(tree, prefix)
            if not remote:
                results[name] = {"status": "error", "changed": [], "error": "No files found at that source."}
                continue
            changed = compare(addon["folder"], remote)
            results[name] = {"status": "update_available" if changed else "up_to_date", "changed": changed,
                             "source": src, "prefix": prefix, "remote": remote}
        except Exception as e:  # network trouble or rate limit: report, never crash the scan
            results[name] = {"status": "error", "changed": [], "error": str(e)}
    return results


def backup_addon(folder: str, backup_dir: str) -> str:
    """Zips the addon folder (including data/) before anything is replaced."""
    os.makedirs(backup_dir, exist_ok=True)
    name = os.path.basename(os.path.normpath(folder))
    zip_path = os.path.join(backup_dir, f"{name}-{time.strftime('%Y%m%d-%H%M%S')}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _dirs, files in os.walk(folder):
            for fn in files:
                full = os.path.join(dirpath, fn)
                z.write(full, os.path.relpath(full, os.path.dirname(folder)))
    return zip_path


def apply_update(folder: str, result: dict, backup_dir: str, get_bytes=_get_bytes) -> str:
    """Downloads every changed file, verifies its hash, then writes it. Returns the backup zip path."""
    src, prefix = result["source"], result["prefix"].strip("/")
    downloads = {}
    for rel in result["changed"]:
        path = f"{prefix}/{rel}" if prefix else rel
        data = get_bytes(f"https://raw.githubusercontent.com/{src['owner']}/{src['repo']}/{src['branch']}/{path}")
        if hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() != result["remote"][rel]:
            raise RuntimeError(f"{rel} didn't match what GitHub reported; nothing was changed.")
        downloads[rel] = data
    backup = backup_addon(folder, backup_dir)
    for rel, data in downloads.items():  # only write once every file downloaded and verified
        target = os.path.join(folder, *rel.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
    return backup
