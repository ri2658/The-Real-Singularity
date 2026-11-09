#!/usr/bin/env python3
"""Upload site/ to the site bucket with explicit content types.

    python scripts/build_site.py                      # refresh site/ first
    python scripts/publish_site.py --dry-run          # list files and types, upload nothing
    python scripts/publish_site.py --bucket BUCKET --distribution DIST_ID
    python scripts/publish_site.py --stack BurgersSiteStack   # read both from the stack outputs

--dir web uploads only the single PINN page (the original week-4 checkpoint).

Content types the checkpoint asks for:
    .wasm -> application/wasm
    .onnx -> application/octet-stream
"""

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".wasm": "application/wasm",
    ".onnx": "application/octet-stream",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", help="S3 bucket (BucketName from the cdk deploy output)")
    parser.add_argument("--distribution", help="CloudFront distribution to invalidate")
    parser.add_argument("--stack", help="CloudFormation stack to read BucketName and DistributionId from")
    parser.add_argument("--dir", default="site", help="folder to upload (default: site)")
    parser.add_argument("--dry-run", action="store_true", help="list what would be uploaded")
    args = parser.parse_args()
    if args.stack and not args.dry_run:
        import boto3
        stack = boto3.client("cloudformation").describe_stacks(StackName=args.stack)["Stacks"][0]
        outputs = {o["OutputKey"]: o["OutputValue"] for o in stack["Outputs"]}
        args.bucket = args.bucket or outputs["BucketName"]
        args.distribution = args.distribution or outputs["DistributionId"]
    if not args.dry_run and not args.bucket:
        parser.error("--bucket is required unless --dry-run")

    WEB = ROOT / args.dir
    if not args.dry_run:
        import boto3
        s3 = boto3.client("s3")
    uploaded = 0
    for path in sorted(WEB.rglob("*")):
        if not path.is_file() or path.suffix == ".md" or path.name.startswith("."):
            continue
        key = path.relative_to(WEB).as_posix()
        content_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        if args.dry_run:
            print(f"{key}  {content_type}")
            uploaded += 1
            continue
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

    if args.distribution and not args.dry_run:
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
