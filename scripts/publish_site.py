#!/usr/bin/env python3
"""Upload web/ to the Burgers site bucket with explicit content types.

    python scripts/publish_site.py --bucket BUCKET --distribution DIST_ID

Content types the checkpoint asks for:
    .wasm -> application/wasm
    .onnx -> application/octet-stream
"""

import argparse
import time
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".wasm": "application/wasm",
    ".onnx": "application/octet-stream",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--distribution", help="CloudFront distribution to invalidate")
    args = parser.parse_args()

    s3 = boto3.client("s3")
    uploaded = 0
    for path in sorted(WEB.rglob("*")):
        if not path.is_file() or path.suffix == ".md" or path.name.startswith("."):
            continue
        key = path.relative_to(WEB).as_posix()
        content_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        s3.upload_file(
            str(path),
            args.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        print(f"{key}  {content_type}")
        uploaded += 1
    if uploaded == 0:
        raise SystemExit(f"no files to upload in {WEB}")

    if args.distribution:
        boto3.client("cloudfront").create_invalidation(
            DistributionId=args.distribution,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": ["/*"]},
                "CallerReference": str(time.time()),
            },
        )
        print(f"invalidated {args.distribution}")


if __name__ == "__main__":
    main()
