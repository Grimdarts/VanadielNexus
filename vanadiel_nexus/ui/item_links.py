"""Open an item on BG-Wiki, FFXIAH or FFXIclopedia: the same menu actions and default site on every page."""
from ..core.wiki import SITES, full_names, is_bg_wiki, item_urls


def _name(row: dict) -> str:
    return str(row.get("name") or row.get("title") or "").strip()


def _urls(ctx, row: dict) -> dict:
    name, item_id = _name(row), row.get("item_id") or row.get("guideItemId")
    full = full_names(ctx.windower_dir).get(item_id) if "." in name and isinstance(item_id, int) else ""
    return item_urls(name, item_id, row.get("wikiUrl", ""), full or "")


def default_site(ctx) -> str:
    site = ctx.settings.get("wiki_site")
    return site if isinstance(site, str) and site in dict(SITES) else SITES[0][0]


def open_item(ctx, row: dict, site: str = "") -> None:
    if row and _name(row):  # a row without a name would only open the site's home page
        ctx.open_url(_urls(ctx, row)[site or default_site(ctx)])


def add_open_actions(menu, ctx, row: dict) -> None:
    """Adds "Open on <site> ↗" for every site, the default site first."""
    first = default_site(ctx)
    for key, label in sorted(SITES, key=lambda site: site[0] != first):
        menu.addAction(f"Open on {label} ↗", lambda key=key: open_item(ctx, row, key))
    saved = str(row.get("wikiUrl") or "")
    if saved.startswith("http") and not is_bg_wiki(saved):  # e.g. the FFXIAH set a tracked guide item came from
        menu.addAction("Open saved link ↗", lambda: ctx.open_url(saved))
