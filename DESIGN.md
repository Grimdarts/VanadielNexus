# Vana'diel Nexus Design System

Status: DRAFT for Jason's approval (2026-10-29). Applies to the Qt (PySide6) rebuild.
Visual preview: `docs/design-preview.html`.

## Feel

A calm, dark companion window that sits next to the game for hours. It borrows the icon's materials: **night-sky navy, crystal cyan, and gold**. Cyan means "you can click this". Gold means "progress and treasure" (gear you own, upgrades, completion). Everything else stays quiet so those two colors carry meaning.

Rules of thumb:
- One bright button per screen, at most. Everything else is quiet.
- Color always means something. No decorative color.
- Readable from a second monitor at arm's length: nothing smaller than 12px, body text 14px.

## Color

| Token | Hex | Use |
|---|---|---|
| `bg` | `#0B1020` | Window background |
| `surface` | `#121A2E` | Sidebar, cards, tables |
| `surface-2` | `#18223A` | Hovered rows, inputs, dropdowns |
| `border` | `#26324D` | Dividers, input outlines |
| `text` | `#E6EAF2` | Main text |
| `text-muted` | `#9AA6BF` | Labels, secondary info |
| `text-faint` | `#7D89A6` | Hints, disabled text |
| `accent` (crystal) | `#22D3EE` | Primary button, links, focus ring, selected item |
| `accent-strong` | `#0EA5C6` | Primary button hover/pressed |
| `gold` | `#E0B04A` | Owned gear, upgrade progress, completion, the app name |
| `success` | `#34D399` | Running / installed / OK |
| `warning` | `#F59E0B` | Needs attention (setup incomplete, conflict) |
| `danger` | `#F87171` | Destructive actions, errors |

Text on `accent` and `gold` fills is `bg` navy, never white. All text/background pairs above meet WCAG AA contrast.

## Typography

| Role | Font | Size / weight |
|---|---|---|
| App name, page titles | **Cinzel** (bundled in resources/fonts, SIL Open Font License; echoes the icon's serif letters) | 22px, 600 |
| Section headings | Segoe UI Variable | 16px, 600 |
| Body, tables, inputs | Segoe UI Variable | 14px, 400 |
| Labels, captions | Segoe UI Variable | 12px, 500 |
| Numbers (counts, stats, item quantities) | Segoe UI Variable, tabular figures | same as context |

A Settings option scales all text 90% to 130%. Qt also follows Windows display scaling, so 4K monitors stay crisp.

## Layout

- **Left sidebar** (220px, collapses to a 64px icon rail below 1000px window width): Gear, Wishlist, Inventory, Addons, Hotkeys, Settings. The selected item gets a cyan bar and cyan text.
- **Top bar** (52px): page title on the left; character and job picker, **Setup status** pill, and update notice on the right.
- **Content**: a toolbar row (search, filters, the page's one primary action), then the main table or cards. Toolbars wrap to a second line instead of overflowing; rarely used actions live in a "⋯ More" menu.
- Minimum window 900×600. The app remembers size, position and monitor.
- Detail panels open on the right side of the content (for example, an addon's settings), and close with Esc.

## Spacing and shape

- 4px grid: 4, 8, 12, 16, 24, 32.
- Page padding 24px; card padding 16px; gap between controls 8px.
- Corner radius: 6px for inputs and buttons, 10px for cards and panels.
- Table rows 36px tall, with a subtle zebra stripe (`surface` / `surface-2` at 50%).

## Components

**Buttons**
- **Primary**: cyan fill, navy text. One per screen (for example "Add gear").
- **Secondary**: `surface-2` fill, `text` color, `border` outline. Most buttons.
- **Ghost**: text only, `text-muted`, for toolbar icons and minor actions.
- **Danger**: red text on secondary style; only a confirmation dialog uses a red fill.

**Inputs and dropdowns**: `surface-2` fill, `border` outline, `text` color, cyan focus ring. Dropdown lists use the same dark colors (the bug that made the old job picker unreadable cannot recur).

**Status pills**: small rounded labels. Success green "Running", gray "Off", warning amber "Setup 2/3", gold "Owned".

**Progress** (REMA stages, JSE upgrades): thin gold bar on a `surface-2` track with the number beside it, for example "19,660 / 30,000".

**Windows title bar**: dark, matching `bg`, using Windows 11's dark title bar setting.

## Motion

Minimal: 120ms color fades on hover and focus, 160ms slide for the detail panel. No bouncing, no glow animations.

## Icon

`assets/VanadielNexus.ico` (crystal, cyan V, gold N). Detailed art at 48px and up, simplified art at 16-32px. Rebuilt with `py tools/make_icon.py`.
