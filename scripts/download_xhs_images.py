#!/usr/bin/env python3
"""Download note images from a xiaohongshu-mcp get_feed_detail JSON response.

Uses Python stdlib only. It looks for a dict containing `imageList`, prefers
`urlDefault`, falls back to `urlPre`, downloads immediately, and writes a
manifest.json describing what was actually downloaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import time
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36"
)
MAX_BYTES_DEFAULT = 30 * 1024 * 1024


def find_image_list(node: Any) -> list[dict[str, Any]]:
    """Find the first imageList array in a nested MCP/HTTP response."""
    if isinstance(node, dict):
        value = node.get("imageList")
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        value = node.get("image_list")
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        for child in node.values():
            found = find_image_list(child)
            if found:
                return found
    elif isinstance(node, list):
        for child in node:
            found = find_image_list(child)
            if found:
                return found
    return []


def candidate_urls(item: dict[str, Any]) -> Iterable[tuple[str, str]]:
    for key in ("urlDefault", "urlPre", "url", "url_default", "url_pre"):
        value = item.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            yield key, value


def extension_for(content_type: str | None, url: str) -> str:
    if content_type:
        content_type = content_type.split(";", 1)[0].strip().lower()
        ext = mimetypes.guess_extension(content_type)
        if ext:
            return ".jpg" if ext == ".jpe" else ext
    lower = url.lower().split("?", 1)[0]
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"):
        if lower.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".img"


def download(url: str, cookie: str | None, timeout: float, max_bytes: int) -> tuple[bytes, str | None]:
    headers = {
        "User-Agent": DEFAULT_UA,
        "Referer": "https://www.xiaohongshu.com/",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    if cookie:
        headers["Cookie"] = cookie
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("Content-Type")
        chunks = []
        total = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"image exceeds max size ({max_bytes} bytes)")
            chunks.append(chunk)
        return b"".join(chunks), content_type


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="get_feed_detail JSON file")
    p.add_argument("--out-dir", required=True, help="directory for downloaded images")
    p.add_argument("--cookie-env", default="XHS_COOKIE", help="optional env var containing XHS cookie")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--max-images", type=int, default=50)
    p.add_argument("--max-bytes", type=int, default=MAX_BYTES_DEFAULT)
    args = p.parse_args()

    src = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(src.read_text(encoding="utf-8"))
    images = find_image_list(payload)[: max(0, args.max_images)]
    cookie = os.getenv(args.cookie_env) or None

    manifest: dict[str, Any] = {
        "source": str(src),
        "image_count_in_payload": len(images),
        "downloaded": 0,
        "failed": 0,
        "images": [],
    }

    for idx, item in enumerate(images, start=1):
        rec: dict[str, Any] = {
            "image_index": idx,
            "width": item.get("width"),
            "height": item.get("height"),
            "status": "failed",
            "attempts": [],
        }

        seen = set()
        success = False
        for key, url in candidate_urls(item):
            if url in seen:
                continue
            seen.add(url)
            for attempt in range(1, args.retries + 2):
                try:
                    data, content_type = download(url, cookie, args.timeout, args.max_bytes)
                    if not data:
                        raise ValueError("empty response")
                    digest = hashlib.sha256(data).hexdigest()[:12]
                    ext = extension_for(content_type, url)
                    path = out_dir / f"{idx:02d}-{digest}{ext}"
                    path.write_bytes(data)
                    rec.update(
                        {
                            "status": "downloaded",
                            "source_key": key,
                            "source_url": url,
                            "local_path": str(path.resolve()),
                            "bytes": len(data),
                            "content_type": content_type,
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
                    )
                    manifest["downloaded"] += 1
                    success = True
                    break
                except (HTTPError, URLError, TimeoutError, ValueError, OSError) as e:
                    rec["attempts"].append(
                        {"source_key": key, "url": url, "attempt": attempt, "error": str(e)}
                    )
                    if attempt <= args.retries:
                        time.sleep(min(0.5 * (2 ** (attempt - 1)), 2.0))
            if success:
                break

        if not success:
            manifest["failed"] += 1
        manifest["images"].append(rec)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
