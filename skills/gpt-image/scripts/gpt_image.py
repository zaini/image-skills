#!/usr/bin/env python3
"""Generate or edit images using OpenAI's Images API (gpt-image-2, gpt-image-1, ...).

No external Python dependencies. Generation uses urllib (plain JSON). Editing shells
out to `curl` for the multipart upload — urllib's hand-rolled multipart body reliably
triggered BrokenPipeError against this endpoint with multiple image[] files, while
curl handles the same request without issue.
"""

import argparse
import base64
import json
import os
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid

API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")

MODELS = {"gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"}
SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}
QUALITIES = {"auto", "high", "medium", "low"}
FORMATS = {"png", "jpeg", "webp"}
BACKGROUNDS = {"auto", "transparent", "opaque"}


def get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    env_file = os.path.expanduser("~/.gpt-image.env")
    if os.path.exists(env_file):
        for line in open(env_file):
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    print("Error: OPENAI_API_KEY not set (env var or ~/.gpt-image.env)", file=sys.stderr)
    sys.exit(1)


def edit_images(url: str, api_key: str, fields: dict, input_paths: list[str]) -> dict:
    """POSTs a multipart/form-data request via curl and returns the parsed JSON response.

    The Authorization header is passed through a curl config file (mode 600) rather
    than argv, so the API key doesn't show up in `ps` output.
    """
    fd, cfg_path = tempfile.mkstemp(suffix=".curlcfg")
    try:
        os.chmod(cfg_path, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "w") as cfg:
            cfg.write(f'header = "Authorization: Bearer {api_key}"\n')

        cmd = ["curl", "-sS", "-K", cfg_path, url]
        for name, value in fields.items():
            cmd += ["-F", f"{name}={value}"]
        for path in input_paths:
            cmd += ["-F", f"image[]=@{path}"]

        result = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        os.unlink(cfg_path)

    if result.returncode != 0:
        print(f"curl failed (exit {result.returncode}): {result.stderr}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Non-JSON response: {result.stdout}", file=sys.stderr)
        sys.exit(1)


def extract_images(result: dict) -> list[bytes]:
    if "error" in result:
        print(f"API error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    images = []
    for item in result.get("data", []):
        if "b64_json" in item:
            images.append(base64.b64decode(item["b64_json"]))
        elif "url" in item:
            with urllib.request.urlopen(item["url"]) as img_resp:
                images.append(img_resp.read())
    if not images:
        print(f"No image data in response: {result}", file=sys.stderr)
        sys.exit(1)
    return images


def generate_images(url: str, api_key: str, payload: dict) -> list[bytes]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    return extract_images(result)


def resolve_output(output: str | None, fmt: str, index: int, total: int) -> str:
    if output:
        base, ext = os.path.splitext(output)
        ext = ext or f".{fmt}"
        out_dir = os.path.dirname(output)
    else:
        out_dir = "screenshots" if os.path.isdir("screenshots") else "."
        base = os.path.join(out_dir, f"gptimage_{uuid.uuid4().hex[:8]}")
        ext = f".{fmt}"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    suffix = f"_{index + 1}" if total > 1 else ""
    return f"{base}{suffix}{ext}"


def add_common_args(p: argparse.ArgumentParser):
    p.add_argument("--prompt", required=True)
    p.add_argument("--model", default="gpt-image-2", choices=sorted(MODELS))
    p.add_argument("--size", default="1024x1024", choices=sorted(SIZES))
    p.add_argument("--quality", default="auto", choices=sorted(QUALITIES))
    p.add_argument("--format", dest="fmt", default="png", choices=sorted(FORMATS))
    p.add_argument("--background", default="auto", choices=sorted(BACKGROUNDS))
    p.add_argument("--n", type=int, default=1)
    p.add_argument("--output")


def main():
    parser = argparse.ArgumentParser(description="Generate or edit images with OpenAI's Images API")
    subparsers = parser.add_subparsers(dest="command")

    gen_p = subparsers.add_parser("generate", help="Generate a new image (default)")
    add_common_args(gen_p)

    edit_p = subparsers.add_parser("edit", help="Edit existing image(s)")
    add_common_args(edit_p)
    edit_p.add_argument("--input", nargs="+", required=True, help="Up to 3 input image paths")

    # Allow `gpt_image.py --prompt ...` without the `generate` subcommand.
    argv = sys.argv[1:]
    if not argv or argv[0] not in ("generate", "edit"):
        argv = ["generate"] + argv

    args = parser.parse_args(argv)
    api_key = get_api_key()

    if args.command == "edit":
        if len(args.input) > 3:
            print("Error: at most 3 input images are supported", file=sys.stderr)
            sys.exit(1)
        for path in args.input:
            if not os.path.isfile(path):
                print(f"Error: input file not found: {path}", file=sys.stderr)
                sys.exit(1)
        fields = {
            "prompt": args.prompt,
            "model": args.model,
            "size": args.size,
            "quality": args.quality,
            "n": str(args.n),
        }
        if args.background != "auto":
            fields["background"] = args.background
        result = edit_images(f"{API_BASE}/images/edits", api_key, fields, args.input)
        images = extract_images(result)
    else:
        payload = {
            "model": args.model,
            "prompt": args.prompt,
            "size": args.size,
            "quality": args.quality,
            "n": args.n,
        }
        if args.background != "auto":
            payload["background"] = args.background
        images = generate_images(f"{API_BASE}/images/generations", api_key, payload)

    paths = []
    for i, image_bytes in enumerate(images):
        path = resolve_output(args.output, args.fmt, i, len(images))
        with open(path, "wb") as f:
            f.write(image_bytes)
        paths.append(path)

    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
