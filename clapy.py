#!/usr/bin/env python3
"""
claude-cli.py — A command-line tool to query Claude models via the Anthropic API.
Supports text prompts, images, and PDF attachments.

Usage:
    python claude-cli.py "What is the meaning of life?"
    python claude-cli.py "Describe this image" --image photo.png
    python claude-cli.py "Summarize this document" --pdf report.pdf
    python claude-cli.py "Compare these" --image a.png --image b.jpg --pdf doc.pdf
    python claude-cli.py "Hello" --model claude-sonnet-4-20250514 --temperature 0.5

Environment:
    ANTHROPIC_API_KEY  — required, your Anthropic API key

Dependencies:
    None beyond Python 3.8+ standard library.
"""

import argparse
import base64
import json
import os
import sys
from http.client import HTTPSConnection
from pathlib import Path


# ---------------------------------------------------------------------------
# Config defaults — easy to change or later load from a file
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 1.0
API_HOST = "api.anthropic.com"
API_PATH = "/v1/messages"
API_VERSION = "2023-06-01"

SUPPORTED_IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

SUPPORTED_PDF_TYPES = {
    ".pdf": "application/pdf",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    """Read API key from environment."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY='sk-ant-...'", file=sys.stderr)
        sys.exit(1)
    return key


def encode_file(filepath: str) -> tuple[str, str]:
    """Read a file from disk and return (base64_data, media_type)."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    ext = path.suffix.lower()
    media_type = SUPPORTED_IMAGE_TYPES.get(ext) or SUPPORTED_PDF_TYPES.get(ext)
    if not media_type:
        print(f"Error: Unsupported file type '{ext}' for {filepath}", file=sys.stderr)
        print(f"  Supported: {', '.join(list(SUPPORTED_IMAGE_TYPES) + list(SUPPORTED_PDF_TYPES))}", file=sys.stderr)
        sys.exit(1)

    data = path.read_bytes()
    b64 = base64.standard_b64encode(data).decode("ascii")
    return b64, media_type


def build_content_blocks(prompt: str, images: list[str], pdfs: list[str]) -> list[dict]:
    """
    Build the 'content' array for the API message.
    Attachments come first so the model sees them before the question.
    """
    blocks = []

    for img_path in images:
        b64, media_type = encode_file(img_path)
        blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64,
            },
        })

    for pdf_path in pdfs:
        b64, media_type = encode_file(pdf_path)
        blocks.append({
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64,
            },
        })

    blocks.append({"type": "text", "text": prompt})
    return blocks


def call_api(
    api_key: str,
    model: str,
    system: str | None,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    stream: bool = False,
) -> dict | None:
    """Send a request to the Anthropic Messages API and return the response."""
    body: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        body["system"] = system
    if stream:
        body["stream"] = True

    payload = json.dumps(body).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
    }

    conn = HTTPSConnection(API_HOST)
    try:
        conn.request("POST", API_PATH, body=payload, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
    finally:
        conn.close()

    if resp.status != 200:
        print(f"API error ({resp.status}):", file=sys.stderr)
        try:
            err = json.loads(raw)
            print(json.dumps(err, indent=2), file=sys.stderr)
        except json.JSONDecodeError:
            print(raw, file=sys.stderr)
        return None

    return json.loads(raw)


def extract_text(response: dict) -> str:
    """Pull the assistant's text out of the API response."""
    parts = []
    for block in response.get("content", []):
        if block.get("type") == "text":
            parts.append(block["text"])
    return "\n".join(parts)


def print_usage(response: dict) -> None:
    """Print token usage stats to stderr."""
    usage = response.get("usage", {})
    inp = usage.get("input_tokens", "?")
    out = usage.get("output_tokens", "?")
    print(f"[tokens: {inp} in / {out} out]", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Query Claude models from the command line.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("prompt", help="Your text prompt / question")
    p.add_argument(
        "--image", action="append", default=[], metavar="FILE",
        help="Attach an image (png/jpg/gif/webp). Repeatable.",
    )
    p.add_argument(
        "--pdf", action="append", default=[], metavar="FILE",
        help="Attach a PDF document. Repeatable.",
    )
    p.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    p.add_argument(
        "--system", default=None, metavar="TEXT",
        help="System prompt to guide Claude's behavior",
    )
    p.add_argument(
        "--temperature", type=float, default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature 0-1 (default: {DEFAULT_TEMPERATURE})",
    )
    p.add_argument(
        "--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
        help=f"Max output tokens (default: {DEFAULT_MAX_TOKENS})",
    )
    p.add_argument(
        "--show-usage", action="store_true",
        help="Print token usage after the response",
    )
    p.add_argument(
        "--raw", action="store_true",
        help="Print the full JSON response instead of just text",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    api_key = get_api_key()

    # Build the user message with any attachments
    content = build_content_blocks(args.prompt, args.image, args.pdf)
    messages = [{"role": "user", "content": content}]

    # Call the API
    response = call_api(
        api_key=api_key,
        model=args.model,
        system=args.system,
        messages=messages,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )

    if response is None:
        sys.exit(1)

    # Output
    if args.raw:
        print(json.dumps(response, indent=2))
    else:
        print(extract_text(response))

    if args.show_usage:
        print_usage(response)


if __name__ == "__main__":
    main()
