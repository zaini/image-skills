---
name: gpt-image
description: Generate or edit images using OpenAI's GPT Image API (gpt-image-2, gpt-image-1.5, gpt-image-1, gpt-image-1-mini). Saves output to screenshots/ and opens the result. Use when the user asks to generate, create, edit, or make an image and mentions OpenAI or GPT specifically, or when OPENAI_API_KEY is available and no other provider is named.
---

Generate or edit images using OpenAI's Images API via the bundled script (`scripts/gpt_image.py`, no external dependencies — pure `urllib`).

## Requirements

- `OPENAI_API_KEY` — read from the environment, or `~/.gpt-image.env` (`OPENAI_API_KEY=...`) as a fallback. Never hardcode it in the script or in chat.
- `OPENAI_API_BASE` (optional) — custom base URL for Azure OpenAI or compatible proxies. Same env/file lookup.

## Models (`--model`)

| Model | Notes |
|---|---|
| `gpt-image-2` | **Default** — latest, best instruction-following and text rendering |
| `gpt-image-1.5` | Mid-tier |
| `gpt-image-1` | First-generation, fallback if `gpt-image-2` errors |
| `gpt-image-1-mini` | Lightweight, faster |

## Sizes (`--size`)

`1024x1024` (default, square) · `1024x1536` (portrait) · `1536x1024` (landscape) · `auto`

## Quality (`--quality`)

`auto` (default) · `high` · `medium` · `low`

## Format (`--format`) / Background (`--background`)

Format: `png` (default) · `jpeg` · `webp`
Background: `auto` (default) · `transparent` (png/webp only) · `opaque`

## Process

1. **Get the prompt** — use the user's description exactly as given, or ask for one. Be descriptive (style, mood, colors, composition) — GPT Image models follow detail closely and are strong at rendering text.

2. **Pick options** — default to `gpt-image-2`, `1024x1024`, `auto` quality/background, `png`. Adjust when the request implies it: logos/icons → square + `transparent` background; social stories → portrait; banners/wallpapers → landscape; "quick draft" → `low` quality; "final version" → `high`.

3. **Generate:**
   ```bash
   python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py --prompt "<prompt>" [--model gpt-image-2] [--size 1024x1024] [--quality auto] [--format png] [--background auto] [--n 1] [--output <path>]
   ```
   If `--output` is omitted, it saves into `screenshots/` (if that dir exists in the project) or the current directory, with an auto-generated filename. The script prints the saved path(s) on stdout, one per line.

4. **Editing an existing image** — use the `edit` subcommand with up to 3 input images:
   ```bash
   python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py edit --prompt "<what to change>" --input image1.png [image2.png image3.png] [--output <path>]
   ```
   Be explicit in the prompt about what to change and what to keep unchanged. This is
   also the right tool when the user wants a *new* asset to match an existing one's
   style exactly (a logo variant, a matching icon set) — pass the existing asset as
   `--input` and describe what to add/change while keeping the rest identical, rather
   than describing the style from scratch as a plain-generation prompt.

5. **Open the result:**
   ```bash
   open <path>
   ```

6. **On error** — the script prints the HTTP status and body to stderr:
   - 401: `OPENAI_API_KEY` missing/invalid — check the environment or `~/.gpt-image.env`
   - 404/model error: retry with `--model gpt-image-1`
   - 400 re: size/quality/background: fall back to the defaults (`auto`/`1024x1024`)

## Examples

```bash
# Basic generation
python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py --prompt "a serene mountain landscape at sunset with a lake"

# Logo with transparent background
python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py --prompt "modern minimalist logo for a tech startup" --size 1024x1024 --quality high --background transparent --output logo.png

# Landscape banner
python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py --prompt "futuristic cityscape with flying cars" --size 1536x1024 --output cityscape.png

# Multiple variations
python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py --prompt "abstract art in the style of Kandinsky" --n 3

# Edit an existing image
python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py edit --prompt "add a rainbow in the sky" --input photo.png --output photo-with-rainbow.png

# Combine multiple reference images
python3 ~/.claude/skills/gpt-image/scripts/gpt_image.py edit --prompt "create a gift basket containing all items shown" --input item1.png item2.png item3.png --output gift-basket.png
```
