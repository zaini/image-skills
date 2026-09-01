# image-skills

## Quick setup

Paste this into Claude Code to clone the repo and install all three skills globally:

```
Clone git@github.com:zaini/image-skills.git into a temp directory, then copy its
skills/gpt-image, skills/gemini-image, and skills/image-compress directories into
~/.claude/skills/ (creating that directory if needed), overwriting if they already
exist. Then confirm the three skill.md files are in place.
```

---

Three Claude Code [skills](https://docs.claude.com/en/docs/claude-code/skills) for
generating, editing, and compressing images from the command line — two use OpenAI's GPT
Image API and Google's Gemini (Imagen) API to create images, the third shrinks any image's
file size afterward. Each skill is a `skill.md` (instructions Claude reads) plus a small
Python script that does the actual work.

```
skills/
  gpt-image/
    skill.md
    scripts/gpt_image.py
  gemini-image/
    skill.md
    scripts/gemini_image.py
  image-compress/
    skill.md
    scripts/compress_image.py
```

## What each one does

- **gpt-image** — generate or edit images with OpenAI's Images API
  (`gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini`). Supports editing an
  existing image (or combining up to 3 reference images) as well as plain text-to-image.
- **gemini-image** — generate images with Google's Gemini API, either Imagen 4
  (`imagen4`, `imagen4-ultra`, `imagen4-fast`) or a Gemini image model
  (`flash`, `pro`, `flash3`). The Gemini models also accept reference images to match an
  existing style or edit an asset directly.
- **image-compress** — shrink an image's file size by resizing and/or re-encoding it
  (WebP, JPEG, or palette-optimized PNG) via Pillow. Useful right after generating an
  image with either skill above, or on any existing image.

`gpt_image.py` and `gemini_image.py` have no third-party dependencies — they use `urllib`
(`gpt_image.py` shells out to `curl` only for multipart image edits). `compress_image.py`
is the one script with a dependency: it needs [Pillow](https://pillow.readthedocs.io/)
(`pip install Pillow`), since real image compression needs an actual codec library.

## Installing as Claude Code skills

Drop each skill directory into `~/.claude/skills/` (or your project's `.claude/skills/`):

```bash
git clone <this-repo-url>
cp -r image-skills/skills/gpt-image ~/.claude/skills/
cp -r image-skills/skills/gemini-image ~/.claude/skills/
```

Claude Code auto-discovers skills under `~/.claude/skills/<name>/skill.md`. Once installed,
just ask Claude to "generate an image of ..." — it picks the right skill based on the
`description` in each `skill.md` (GPT Image is preferred by default if `OPENAI_API_KEY` is
set; otherwise Gemini is used).

## Running the scripts directly (no Claude Code required)

Both scripts are plain Python 3, so you can call them yourself.

### GPT Image

Requires `OPENAI_API_KEY` in your environment, or a `~/.gpt-image.env` file containing
`OPENAI_API_KEY=sk-...`. Optionally set `OPENAI_API_BASE` to point at Azure OpenAI or a
compatible proxy.

```bash
# Generate
python3 skills/gpt-image/scripts/gpt_image.py \
  --prompt "a serene mountain landscape at sunset with a lake"

# Generate with options
python3 skills/gpt-image/scripts/gpt_image.py \
  --prompt "modern minimalist logo for a tech startup" \
  --model gpt-image-2 --size 1024x1024 --quality high \
  --background transparent --output logo.png

# Multiple variations
python3 skills/gpt-image/scripts/gpt_image.py \
  --prompt "abstract art in the style of Kandinsky" --n 3

# Edit an existing image
python3 skills/gpt-image/scripts/gpt_image.py edit \
  --prompt "add a rainbow in the sky" \
  --input photo.png --output photo-with-rainbow.png

# Combine multiple reference images into one edit
python3 skills/gpt-image/scripts/gpt_image.py edit \
  --prompt "create a gift basket containing all items shown" \
  --input item1.png item2.png item3.png --output gift-basket.png
```

Flags:

| Flag | Values | Default |
|---|---|---|
| `--model` | `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini` | `gpt-image-2` |
| `--size` | `1024x1024`, `1024x1536`, `1536x1024`, `auto` | `1024x1024` |
| `--quality` | `auto`, `high`, `medium`, `low` | `auto` |
| `--format` | `png`, `jpeg`, `webp` | `png` |
| `--background` | `auto`, `transparent` (png/webp only), `opaque` | `auto` |
| `--n` | number of images | `1` |
| `--output` | output file path | auto-named into `screenshots/` or cwd |

If `--output` is omitted, the image is saved into a `screenshots/` directory (created if it
doesn't exist) with an auto-generated filename, and the path is printed to stdout.

`edit` accepts up to 3 `--input` images.

### Gemini / Imagen

Requires `GEMINI_API_KEY` in your environment.

```bash
# Imagen 4 (default, best quality)
python3 skills/gemini-image/scripts/gemini_image.py \
  "a neon-lit street market at night, cinematic" imagen4 screenshots

# Ultra quality
python3 skills/gemini-image/scripts/gemini_image.py \
  "portrait of a woman in traditional dress" imagen4-ultra screenshots

# Fast generation
python3 skills/gemini-image/scripts/gemini_image.py \
  "app icon for a finance app, minimal" imagen4-fast screenshots

# Gemini image model with a reference image (style match / direct edit)
python3 skills/gemini-image/scripts/gemini_image.py \
  "make this logo blue and add a lightning bolt" flash screenshots \
  --ref path/to/existing-logo.png
```

Usage: `gemini_image.py <prompt> [model] [output_dir] [-r/--ref <image_path>]...`

| Alias | Model | Notes |
|---|---|---|
| `imagen4` | imagen-4.0-generate-001 | Default — best quality |
| `imagen4-ultra` | imagen-4.0-ultra-generate-001 | Highest quality, slower |
| `imagen4-fast` | imagen-4.0-fast-generate-001 | Fastest |
| `flash` | gemini-2.5-flash-image | Supports `--ref` |
| `pro` | gemini-3-pro-image | Supports `--ref` |
| `flash3` | gemini-3.1-flash-image | Supports `--ref` |

`-r/--ref` (repeatable) is only supported by the Gemini models (`flash`, `pro`, `flash3`),
not the `imagen4*` aliases — use it to match an existing visual style or edit an image
directly instead of describing the style from scratch in text.

If `output_dir` is omitted it defaults to `screenshots/` (created if missing). The saved
file path is printed to stdout.

## Errors

**GPT Image** — the script prints the HTTP status and body to stderr:
- `401` — `OPENAI_API_KEY` missing or invalid
- `404` / model error — retry with `--model gpt-image-1`
- `400` re: size/quality/background — fall back to the defaults (`auto` / `1024x1024`)

**Gemini** — the script prints the HTTP body to stderr:
- `403` — `GEMINI_API_KEY` not set or invalid
- `404` — wrong model name; pick another alias from the table above

## Notes

- Neither script hardcodes an API key — both read from the environment (with `gpt_image.py`
  also falling back to `~/.gpt-image.env`). Never commit real keys into this repo.
- Both scripts are dependency-free stdlib Python 3 (`gpt_image.py`'s image-edit path shells
  out to `curl` for reliable multipart uploads).
