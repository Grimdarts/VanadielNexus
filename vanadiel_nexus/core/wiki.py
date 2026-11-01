"""Wiki links: build BG-Wiki / FFXIAH / FFXIclopedia URLs and parse pasted URLs back into item names."""
import os
import re
import urllib.parse

# Sites an item can be opened on, in menu order: (key, label)
SITES = (("bgwiki", "BG-Wiki"), ("ffxiah", "FFXIAH"), ("ffxiclopedia", "FFXIclopedia"))


def is_bg_wiki(url: str) -> bool:
    host = (urllib.parse.urlparse(url or "").hostname or "").lower()
    return host == "bg-wiki.com" or host.endswith(".bg-wiki.com")


_FULL_NAMES = {}  # items.lua path -> {item id: full name}, read once


def full_names(windower_dir: str) -> dict:
    """Full names for items the game shortens ("Chas. Culottes +3" -> "Chasseur's Culottes +3").

    Read from Windower's own res/items.lua, which every player has. BG-Wiki titles its pages by the short names,
    but FFXIclopedia uses full ones. Empty when Windower isn't found.
    """
    path = os.path.join(windower_dir or "", "res", "items.lua")
    if path not in _FULL_NAMES:
        names = {}
        try:
            with open(path, encoding="utf-8", errors="replace") as source:
                for line in source:
                    match = re.search(r'\bid=(\d+),en="([^"]*\.[^"]*)",ja="[^"]*",enl="([^"]+)"', line)
                    if match:
                        names[int(match[1])] = " ".join(
                            word if i and word in ("of", "the", "and") else re.sub(r"[A-Za-z]", lambda m: m[0].upper(), word, count=1)
                            for i, word in enumerate(match[3].split(" ")))
        except OSError:
            pass
        _FULL_NAMES[path] = names
    return _FULL_NAMES[path]


def item_urls(name: str, item_id=None, wiki_url: str = "", full_name: str = "") -> dict:
    """One URL per site in SITES for an item.

    wiki_url is a saved link (e.g. a wishlist row's wikiUrl). It is only used for BG-Wiki when it really is a
    bg-wiki.com page, so a stored FFXIAH set link can never open from a BG-Wiki action. FFXIAH goes straight to
    the item page when the item ID is known. full_name (see full_names) replaces a shortened name on FFXIclopedia.
    """
    custom = wiki_url if is_bg_wiki(wiki_url) else ""
    urls = build_wiki_urls(name, custom)
    if full_name:
        urls["ffxiclopedia"] = build_wiki_urls(full_name)["ffxiclopedia"]
    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        item_id = 0
    if item_id > 0:
        urls["ffxiah"] = f"https://www.ffxiah.com/item/{item_id}"
    return urls


def build_wiki_urls(item_name: str, custom_bg_url: str = "") -> dict:
    """Return URLs for BG-Wiki, FFXIAH, and FFXIclopedia for a given FFXI item name."""
    clean = (item_name or "").strip()
    # Strip trailing quantity or stage tags in parentheses if present
    clean = re.sub(r"\s*\((?:Stage|iLvl|119|x\d+|Total).*?\)\s*$", "", clean, flags=re.IGNORECASE).strip()
    if not clean:
        return {
            "bgwiki": "https://www.bg-wiki.com",
            "ffxiah": "https://www.ffxiah.com",
            "ffxiclopedia": "https://ffxiclopedia.fandom.com"
        }
    bg_slug = urllib.parse.quote(clean.replace(" ", "_"), safe="_-.'()")
    q_slug = urllib.parse.quote_plus(clean)
    return {
        "bgwiki": custom_bg_url if (custom_bg_url and "bg-wiki.com" in custom_bg_url) else f"https://www.bg-wiki.com/ffxi/{bg_slug}",
        "ffxiah": f"https://www.ffxiah.com/search/item?q={q_slug}",
        "ffxiclopedia": f"https://ffxiclopedia.fandom.com/wiki/{bg_slug}"
    }


def parse_wiki_url_or_name(raw_input: str) -> dict:
    """
    Accepts a BG-Wiki URL, FFXIAH URL, FFXIclopedia URL, or raw item name.
    Extracts the item name and optional metadata.
    """
    s = (raw_input or "").strip()
    if not s:
        return {"name": "", "wikiUrl": "", "source_site": ""}

    if s.startswith("http://") or s.startswith("https://"):
        parsed = urllib.parse.urlparse(s)
        host = parsed.netloc.lower()
        path = urllib.parse.unquote(parsed.path)
        item_name = ""

        if "bg-wiki.com" in host:
            # e.g. /ffxi/Sakpata's_Helm or /ffxi/Boii_Earring_+2
            slug = path.split("/ffxi/")[-1] if "/ffxi/" in path else path.strip("/").split("/")[-1]
            item_name = slug.replace("_", " ").strip()
            source_site = "BG-Wiki"
        elif "ffxiclopedia" in host:
            slug = path.split("/wiki/")[-1] if "/wiki/" in path else path.strip("/").split("/")[-1]
            item_name = slug.replace("_", " ").strip()
            source_site = "FFXIclopedia"
        elif "ffxiah.com" in host:
            qs = urllib.parse.parse_qs(parsed.query)
            if "q" in qs and qs["q"]:
                item_name = qs["q"][0].strip()
            else:
                slug = path.strip("/").split("/")[-1]
                item_name = slug.replace("-", " ").replace("_", " ").strip()
            source_site = "FFXIAH"
        else:
            slug = path.strip("/").split("/")[-1]
            item_name = slug.replace("_", " ").strip()
            source_site = host

        # Optional lightweight title check if item_name is numeric (e.g. ffxiah.com/item/21565)
        if item_name.isdigit():
            try:
                req = urllib.request.Request(s, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    html = resp.read(32768).decode("utf-8", errors="ignore")
                    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
                    if m:
                        t_txt = m.group(1).split("-")[0].split("|")[0].strip()
                        if t_txt:
                            item_name = t_txt
            except Exception:
                item_name = f"FFXIAH Item #{item_name}"

        urls = build_wiki_urls(item_name, s if "bg-wiki.com" in host else "")
        return {
            "name": item_name,
            "wikiUrl": urls["bgwiki"],
            "ffxiahUrl": urls["ffxiah"],
            "ffxiclopediaUrl": urls["ffxiclopedia"],
            "source_site": source_site
        }
    else:
        urls = build_wiki_urls(s)
        return {
            "name": s,
            "wikiUrl": urls["bgwiki"],
            "ffxiahUrl": urls["ffxiah"],
            "ffxiclopediaUrl": urls["ffxiclopedia"],
            "source_site": "Manual / Direct Name"
        }
