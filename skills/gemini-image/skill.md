---
name: gemini-image
description: Generate images using Google's Gemini API (Imagen 4 or Gemini image models) from a text prompt. Saves output to screenshots/ and opens the result. Use when the user asks to generate, create, or make an image.
---

Generate an image using the Gemini API via the bundled script.

## Models (CLI alias → actual model)

| Alias | Model | Notes |
|---|---|---|
| `imagen4` | imagen-4.0-generate-001 | **Default** — best quality |
| `imagen4-ultra` | imagen-4.0-ultra-generate-001 | Highest quality, slower |
| `imagen4-fast` | imagen-4.0-fast-generate-001 | Fastest |
| `flash` | gemini-2.5-flash-image | Gemini Flash with image output |
| `pro` | gemini-3-pro-image | Gemini 3 Pro image |
| `flash3` | gemini-3.1-flash-image | Gemini 3.1 Flash image |

## Process

1. **Get the prompt** — use the user's description exactly as given, or ask for one.

2. **Pick the model** — default to `imagen4` unless the user asks for speed (`imagen4-fast`), maximum quality (`imagen4-ultra`), or a Gemini model.

3. **Determine output dir** — use `screenshots/` if it exists in the current project (per CLAUDE.md convention), otherwise use the current directory.

4. **Run the script:**
   ```bash
   python3 ~/.claude/skills/gemini-image/scripts/gemini_image.py "<prompt>" <model> <output_dir>
   ```
   The script prints the saved file path on stdout.

   **Matching or editing an existing image** — pass it with `-r/--ref path/to/image.png`
   (repeatable; only supported by `flash`/`pro`/`flash3`, not the `imagen4*` aliases).
   Use this whenever the user wants a new asset to look like it was drawn by the same
   hand as one that already exists (a logo restyle, a consistent icon set, "make this
   look like that other one but with X changed") instead of describing the existing
   style from scratch in text:
   ```bash
   python3 ~/.claude/skills/gemini-image/scripts/gemini_image.py \
     "<prompt describing what to keep and what to change>" flash <output_dir> \
     --ref path/to/existing-asset.png
   ```

5. **Open the image:**
   ```bash
   open <path>
   ```

6. **On error** — the script prints the HTTP body to stderr. Common fixes:
   - 403: `GEMINI_API_KEY` not set — check `~/.claude/settings.json` under `env`
   - 404: wrong model name — pick another alias from the table above
   - Try a different model if one fails

## Examples

```bash
# Imagen 4 (default, best quality)
python3 ~/.claude/skills/gemini-image/scripts/gemini_image.py "a neon-lit souk in Baghdad at night, cinematic" imagen4 screenshots

# Ultra quality
python3 ~/.claude/skills/gemini-image/scripts/gemini_image.py "portrait of a woman in traditional Iraqi dress" imagen4-ultra screenshots

# Fast generation
python3 ~/.claude/skills/gemini-image/scripts/gemini_image.py "app icon for a remittance app, minimal" imagen4-fast screenshots
```
