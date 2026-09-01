#!/usr/bin/env python3
"""Generate images using the Gemini API and save them to the screenshots/ folder."""

import sys
import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime

# Available models (use the short alias on the CLI)
MODELS = {
    "imagen4":       "imagen-4.0-generate-001",
    "imagen4-ultra": "imagen-4.0-ultra-generate-001",
    "imagen4-fast":  "imagen-4.0-fast-generate-001",
    "flash":         "gemini-2.5-flash-image",
    "pro":           "gemini-3-pro-image",
    "flash3":        "gemini-3.1-flash-image",
}

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def generate_with_imagen(api_key: str, model_id: str, prompt: str) -> tuple[bytes, str]:
    """Uses the Vertex-style :predict endpoint for Imagen models."""
    url = f"{BASE_URL}/{model_id}:predict?key={api_key}"
    payload = {"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1}}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    preds = result.get("predictions", [])
    if not preds:
        raise ValueError("No predictions returned by Imagen")
    pred = preds[0]
    mime = pred.get("mimeType", "image/png")
    ext = mime.split("/")[-1].replace("jpeg", "jpg")
    return base64.b64decode(pred["bytesBase64Encoded"]), ext


def _guess_mime(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }.get(ext, "image/png")


def generate_with_gemini(
    api_key: str, model_id: str, prompt: str, ref_paths: list[str] | None = None
) -> tuple[bytes, str]:
    """Uses the :generateContent endpoint for Gemini image models.

    `ref_paths` are reference/style images sent alongside the text prompt —
    Gemini's image models can look at them to match an existing style, edit
    an existing asset, or keep a subject consistent across a set.
    """
    url = f"{BASE_URL}/{model_id}:generateContent?key={api_key}"
    parts = []
    for ref_path in ref_paths or []:
        with open(ref_path, "rb") as f:
            ref_bytes = f.read()
        parts.append(
            {
                "inlineData": {
                    "mimeType": _guess_mime(ref_path),
                    "data": base64.b64encode(ref_bytes).decode(),
                }
            }
        )
    parts.append({"text": prompt})
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    image_part = next((p for p in parts if "inlineData" in p), None)
    if not image_part:
        raise ValueError("No image part in Gemini response")
    mime = image_part["inlineData"]["mimeType"]
    ext = mime.split("/")[-1].replace("jpeg", "jpg")
    return base64.b64decode(image_part["inlineData"]["data"]), ext


def _parse_args(argv: list[str]) -> tuple[list[str], list[str]]:
    """Pulls repeatable `-r/--ref <path>` flags out of argv, returns (positional, ref_paths)."""
    positional = []
    ref_paths = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-r", "--ref"):
            if i + 1 >= len(argv):
                print(f"Error: {arg} requires a path argument", file=sys.stderr)
                sys.exit(1)
            ref_paths.append(argv[i + 1])
            i += 2
        else:
            positional.append(arg)
            i += 1
    return positional, ref_paths


def main():
    positional, ref_paths = _parse_args(sys.argv[1:])

    if len(positional) < 1:
        print(
            "Usage: gemini_image.py <prompt> [model] [output_dir] [-r/--ref <image_path>]...\n"
            f"Models: {', '.join(MODELS)} (default: imagen4)\n"
            "-r/--ref points to a reference/style image (repeatable) — Gemini image models\n"
            "(flash/pro/flash3) can match its style or edit it directly. Not supported by\n"
            "the imagen4* aliases, which only accept a text prompt.",
            file=sys.stderr,
        )
        sys.exit(1)

    prompt = positional[0]
    model_alias = positional[1] if len(positional) > 1 else "imagen4"
    output_dir = positional[2] if len(positional) > 2 else "screenshots"

    if model_alias not in MODELS:
        print(f"Unknown model '{model_alias}'. Choose from: {', '.join(MODELS)}", file=sys.stderr)
        sys.exit(1)

    if ref_paths and model_alias.startswith("imagen"):
        print(
            f"Error: reference images (-r/--ref) aren't supported by '{model_alias}' — "
            "use flash, pro, or flash3 instead.",
            file=sys.stderr,
        )
        sys.exit(1)

    for ref_path in ref_paths:
        if not os.path.isfile(ref_path):
            print(f"Error: reference image not found: {ref_path}", file=sys.stderr)
            sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_id = MODELS[model_alias]

    try:
        if model_alias.startswith("imagen"):
            image_bytes, ext = generate_with_imagen(api_key, model_id, prompt)
        else:
            image_bytes, ext = generate_with_gemini(api_key, model_id, prompt, ref_paths)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    safe_prompt = prompt[:40].replace(" ", "_").replace("/", "-")
    filename = f"{output_dir}/gemini_{safe_prompt}_{timestamp}.{ext}"
    with open(filename, "wb") as f:
        f.write(image_bytes)

    print(filename)


if __name__ == "__main__":
    main()
