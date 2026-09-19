#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["rembg[cpu]", "pillow"]
# ///
"""Remove image backgrounds locally with rembg — no API key, runs on your machine.

Requires rembg: pip install "rembg[cpu]"  (Python 3.11-3.13)
Or run this script with `uv run`, which installs rembg from the header above.
"""

import argparse
import os
import sys
import time

try:
    from PIL import Image, ImageColor
    from rembg import new_session, remove
except ImportError:
    print(
        'Error: rembg is required. Install it with: pip install "rembg[cpu]" '
        "(Python 3.11-3.13), or run this script with `uv run`.",
        file=sys.stderr,
    )
    sys.exit(1)

# Curated subset of rembg's models. rembg's own default, bria-rmbg, is left out:
# its licence requires a paid agreement for commercial use.
MODELS = [
    "birefnet-general",
    "birefnet-general-lite",
    "birefnet-portrait",
    "isnet-general-use",
    "silueta",
]
DEFAULT_MODEL = "birefnet-general-lite"
OUTPUT_FORMATS = {".png": "PNG", ".webp": "WEBP", ".jpg": "JPEG", ".jpeg": "JPEG"}


def remove_one(
    path: str,
    out_path: str,
    session,
    alpha_matting: bool,
    only_mask: bool,
    bgcolor: tuple[int, int, int, int] | None,
) -> None:
    pillow_fmt = OUTPUT_FORMATS[os.path.splitext(out_path)[1].lower()]

    with Image.open(path) as img:
        result = remove(
            img,
            session=session,
            alpha_matting=alpha_matting,
            only_mask=only_mask,
            bgcolor=bgcolor or (0, 0, 0, 0),
        )

    if pillow_fmt == "JPEG" and result.mode != "L":
        result = result.convert("RGB")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    result.save(out_path, pillow_fmt)


def resolve_output(input_path: str, out_dir: str | None, only_mask: bool) -> str:
    base = os.path.splitext(os.path.basename(input_path))[0]
    suffix = "mask" if only_mask else "nobg"
    directory = out_dir or os.path.dirname(input_path) or "."
    return os.path.join(directory, f"{base}_{suffix}.png")


def main():
    parser = argparse.ArgumentParser(description="Remove image backgrounds locally with rembg")
    parser.add_argument("--input", nargs="+", required=True, help="Input image path(s)")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=MODELS,
                         help=f"Segmentation model (default: {DEFAULT_MODEL})")
    parser.add_argument("--alpha-matting", action="store_true",
                         help="Refine soft edges (hair, fur, glass); can be slower on large images")
    parser.add_argument("--bgcolor",
                         help="Fill the background with a colour instead of transparency "
                              "(e.g. white, '#ff8800')")
    parser.add_argument("--only-mask", action="store_true",
                         help="Output the black/white cutout mask instead of the cutout")
    parser.add_argument("--output", help="Output path, .png/.webp/.jpg (single input only)")
    parser.add_argument("--output-dir", help="Directory for output files (multiple inputs)")
    args = parser.parse_args()

    if args.output and len(args.input) > 1:
        print("Error: --output only works with a single --input; use --output-dir for multiple", file=sys.stderr)
        sys.exit(1)
    if args.only_mask and args.bgcolor:
        print("Error: --only-mask and --bgcolor can't be combined", file=sys.stderr)
        sys.exit(1)

    for path in args.input:
        if not os.path.isfile(path):
            print(f"Error: input file not found: {path}", file=sys.stderr)
            sys.exit(1)

    bgcolor = None
    if args.bgcolor:
        try:
            bgcolor = ImageColor.getcolor(args.bgcolor, "RGBA")
        except ValueError:
            print(f"Error: unrecognised colour for --bgcolor: {args.bgcolor}", file=sys.stderr)
            sys.exit(1)

    jobs = [(p, args.output or resolve_output(p, args.output_dir, args.only_mask)) for p in args.input]

    # Validate every output up front so a bad flag fails before the model loads/downloads.
    for _, out_path in jobs:
        ext = os.path.splitext(out_path)[1].lower()
        if ext not in OUTPUT_FORMATS:
            print(f"Error: unsupported output extension '{ext}' (use .png, .webp, or .jpg)", file=sys.stderr)
            sys.exit(1)
        if OUTPUT_FORMATS[ext] == "JPEG" and not (bgcolor or args.only_mask):
            print("Error: JPEG can't store transparency — use .png/.webp, or pass --bgcolor", file=sys.stderr)
            sys.exit(1)

    print(f"Loading model '{args.model}' (downloaded on first use, then cached)...", file=sys.stderr)
    session = new_session(args.model)

    for path, out_path in jobs:
        start = time.perf_counter()
        remove_one(path, out_path, session, args.alpha_matting, args.only_mask, bgcolor)
        print(f"{out_path}  ({time.perf_counter() - start:.1f}s)")


if __name__ == "__main__":
    main()
