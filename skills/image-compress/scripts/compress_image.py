#!/usr/bin/env python3
"""Compress image files (resize + re-encode) using Pillow.

Requires Pillow: pip install Pillow
"""

import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install it with: pip install Pillow", file=sys.stderr)
    sys.exit(1)

FORMATS = {"jpeg", "jpg", "png", "webp"}


def compress_one(
    path: str,
    out_path: str,
    fmt: str,
    quality: int,
    max_dimension: int | None,
    strip_metadata: bool,
) -> tuple[int, int]:
    with Image.open(path) as img:
        original_mode = img.mode

        if max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        save_kwargs = {}
        pillow_fmt = "JPEG" if fmt in ("jpeg", "jpg") else fmt.upper()

        if pillow_fmt == "JPEG":
            if original_mode in ("RGBA", "P"):
                img = img.convert("RGB")
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        elif pillow_fmt == "WEBP":
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 6
        elif pillow_fmt == "PNG":
            save_kwargs["optimize"] = True
            # PNG is lossless; "quality" maps to palette compression effort only.
            if quality < 100:
                img = img.convert("P", palette=Image.ADAPTIVE, colors=max(2, quality * 2))

        if strip_metadata:
            data = list(img.getdata())
            stripped = Image.new(img.mode, img.size)
            stripped.putdata(data)
            img = stripped

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        img.save(out_path, pillow_fmt, **save_kwargs)

    return os.path.getsize(path), os.path.getsize(out_path)


def resolve_output(input_path: str, fmt: str, out_dir: str | None) -> str:
    base = os.path.splitext(os.path.basename(input_path))[0]
    ext = "jpg" if fmt in ("jpeg", "jpg") else fmt
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        return os.path.join(out_dir, f"{base}_compressed.{ext}")
    directory = os.path.dirname(input_path) or "."
    return os.path.join(directory, f"{base}_compressed.{ext}")


def main():
    parser = argparse.ArgumentParser(description="Compress image file size via resize + re-encode")
    parser.add_argument("--input", nargs="+", required=True, help="Input image path(s)")
    parser.add_argument("--format", dest="fmt", default="webp", choices=sorted(FORMATS),
                         help="Output format (default: webp — smallest for most photos/art)")
    parser.add_argument("--quality", type=int, default=80,
                         help="0-100, lower = smaller file, more artifacts (default: 80)")
    parser.add_argument("--max-dimension", type=int, default=None,
                         help="Downscale so the longer edge is at most this many pixels")
    parser.add_argument("--strip-metadata", action="store_true",
                         help="Drop EXIF/ICC metadata to shave a little extra size")
    parser.add_argument("--output", help="Output path (single input only)")
    parser.add_argument("--output-dir", help="Directory for output files (multiple inputs)")
    args = parser.parse_args()

    if args.output and len(args.input) > 1:
        print("Error: --output only works with a single --input; use --output-dir for multiple", file=sys.stderr)
        sys.exit(1)

    for path in args.input:
        if not os.path.isfile(path):
            print(f"Error: input file not found: {path}", file=sys.stderr)
            sys.exit(1)

    total_before = total_after = 0
    for path in args.input:
        out_path = args.output if args.output else resolve_output(path, args.fmt, args.output_dir)
        before, after = compress_one(
            path, out_path, args.fmt, args.quality, args.max_dimension, args.strip_metadata
        )
        total_before += before
        total_after += after
        pct = 100 * (1 - after / before) if before else 0
        print(f"{out_path}  ({before/1024:.1f} KB -> {after/1024:.1f} KB, -{pct:.0f}%)")

    if len(args.input) > 1 and total_before:
        pct = 100 * (1 - total_after / total_before)
        print(f"Total: {total_before/1024:.1f} KB -> {total_after/1024:.1f} KB (-{pct:.0f}%)")


if __name__ == "__main__":
    main()
