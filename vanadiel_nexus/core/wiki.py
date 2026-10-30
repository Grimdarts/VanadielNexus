"""Wiki links: build BG-Wiki / FFXIAH / FFXIclopedia URLs and parse pasted URLs back into item names."""
import re
import urllib.parse


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
