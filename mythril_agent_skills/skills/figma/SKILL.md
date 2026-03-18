---
name: figma
description: >
  Fetch Figma design data from a URL and inject specs (layout, colors, typography,
  components) into context. Use when user shares a Figma link and asks to implement,
  inspect, or code a design. Trigger on ANY message containing a figma.com URL,
  or when the user asks about colors/spacing/fonts from a design, or says
  "implement this design", "what does the design look like", "according to Figma",
  "from the design file".
license: Apache-2.0
---

# When to Use This Skill

- A message contains a `figma.com` URL (design, file, proto)
- User asks about colors, spacing, fonts, or dimensions from a design
- User wants to implement, match, or code a component from a design
- User says "according to Figma", "from the design", "in the mockup"

# Prerequisites

Requires `FIGMA_ACCESS_TOKEN` environment variable. See `README.md` in this skill directory for setup instructions.

# Workflow

1. Extract the Figma URL from the user's message
2. Run `figma_fetch.py` to get structured design specs
3. If fetch succeeds → read the markdown output, use the specs to generate accurate code
4. If fetch fails with 429 → **fall back to image export** (see "Fallback" below)

## Running the Scripts

Two scripts are available in `scripts/` relative to this skill directory. Both require only Python 3.8+ standard library (zero dependencies).

### Fetch design specs (figma_fetch.py) — primary

```bash
# Inspect a specific node (most common — URL contains node-id)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# File overview (no node-id in URL)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name"

# Limit tree depth (default: 5)
python3 scripts/figma_fetch.py "https://..." --depth 3
```

| Flag | Default | Description |
|---|---|---|
| `--depth N` | `5` | Max recursion depth into child nodes. Use `2`–`3` for large frames to avoid truncation. |

### Export node as image (figma_export.py) — secondary / fallback

Downloads a rendered image of a specific node to disk and prints the saved file path. Use as a **fallback** when `figma_fetch.py` hits 429 (see "Fallback" section), or alongside fetch to provide visual reference.

**Bash (macOS / Linux):**
```bash
CACHE_DIR="$(realpath "${TMPDIR:-/tmp}")/mythril-skills-cache/figma"
mkdir -p "$CACHE_DIR"
python3 scripts/figma_export.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" \
  --format png --scale 2 --output "$CACHE_DIR/node_1-2.png"
```

**PowerShell (Windows):**
```powershell
$CACHE_DIR = Join-Path ([IO.Path]::GetFullPath([IO.Path]::GetTempPath())) "mythril-skills-cache/figma"
New-Item -ItemType Directory -Force -Path $CACHE_DIR | Out-Null
python3 scripts/figma_export.py "https://www.figma.com/design/ABC123/Name?node-id=1-2" `
  --format png --scale 2 --output "$CACHE_DIR/node_1-2.png"
```

**Automatic access**: All files under the cache directory are skill-managed temporary artifacts created by this skill. Read, write, and delete them **automatically without asking the user for confirmation** — they are ephemeral and trusted.

| Flag | Default | Description |
|---|---|---|
| `--format` | `png` | Image format: `png`, `jpg`, `svg`, or `pdf` |
| `--scale` | `2.0` | Export scale factor 0.01–4 (e.g. `2` for @2x retina) |
| `--output PATH` | `./figma_<node-id>.<format>` | Destination file path. **Always use the cache dir above for temp exports.** |

Prints the **absolute path** of the saved file on success. Use that path to load the image for visual analysis.

Exit codes: 0 = success, 1 = API error, 2 = bad arguments. On error, surface the printed message to the user.

## Handling 429 Rate Limit errors

Both scripts fail immediately on 429 — **no automatic retry**. Do NOT attempt alternative approaches (no browser/playwright, no screenshots, no web-fetching the Figma URL).

### Fallback: fetch 429 → try image export

When `figma_fetch.py` returns 429, attempt `figma_export.py` as a visual fallback (both use Tier 1 endpoints but may have separate quota remaining):

1. Run `figma_export.py` with `--output` pointing to the cache dir (see example above)
2. If export succeeds → load the image for visual analysis and **tell the user explicitly**:
   - "I could not get the structured design data (API quota exceeded), so I exported an image instead."
   - "The image shows the visual appearance, but I do NOT have exact property values (spacing in px, font sizes, colors as hex, border-radius, etc.). These values may be approximate if I infer them from the image."
3. If export also fails with 429 → stop. Report the error to the user:
   - **`limit_type: low`**: Monthly quota exhausted (View/Collab seat = 6 calls/month on Tier 1). Suggest upgrading to a **Dev or Full seat**.
   - **`limit_type: high`**: Per-minute burst limit (Dev/Full seat). Suggest waiting the seconds shown in the error.

### Clean up exported images

**This step is MANDATORY — always execute it after you are done analyzing the image, even if errors occurred.**

```bash
rm -f "$CACHE_DIR/node_1-2.png"  # delete the specific file you exported
```

If leftovers accumulate from interrupted sessions, the user can run `skills-clean-cache`.

## Using the Output

**figma_fetch.py** outputs structured markdown covering all visual and layout properties present on each node. The exact fields vary by node type — a FRAME with auto-layout produces different output than a TEXT node. Read what's there; don't expect every section to appear on every node.

Typical sections include layout dimensions, fills/strokes, effects, typography (TEXT nodes), component metadata, and design token bindings. Use these values to generate accurate CSS or UI code matching the design. When a section is absent, the node doesn't have that property set.

**figma_export.py** outputs an image file. You can analyze the image visually, but you will NOT have structured property data (exact dimensions, colors, font specs, padding, etc.). Always caveat to the user that values inferred from the image are approximate.
