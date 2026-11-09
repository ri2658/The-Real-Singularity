"""Build the site and publish it to S3 + CloudFront in one step.

Run from the repo root:
    python scripts/deploy.py             # build, sign in if needed, upload, refresh CloudFront
    python scripts/deploy.py --dry-run   # build and list what would be uploaded

What it does:
  1. Rebuilds site/ (scripts/build_site.py), so the upload always matches the sources.
  2. Reuses your current AWS sign-in. If there is none, or it has expired, it runs
     `aws login` (a browser window opens) and carries on.
  3. Reads the bucket name and CloudFront distribution from the BurgersSiteStack
     outputs, so nothing is hard-coded.
  4. Uploads site/ with the right content types (scripts/publish_site.py) and
     refreshes CloudFront.

Needs the AWS CLI (Windows: winget install -e --id Amazon.AWSCLI). boto3 is
installed automatically if missing.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STACK = "BurgersSiteStack"
DEFAULT_REGION = "us-east-2"


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, **kw)


def ensure_boto3():
    try:
        import boto3  # noqa: F401
    except ImportError:
        print("boto3 is missing; installing it ...")
        if run([sys.executable, "-m", "pip", "install", "-q", "boto3"]).returncode:
            sys.exit("Could not install boto3. Run: python -m pip install boto3")


def signed_in():
    """Return the account id if the current credentials work, else None."""
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    try:
        return boto3.client("sts").get_caller_identity()["Account"]
    except (BotoCoreError, ClientError):
        return None


def load_cli_login():
    """Copy the AWS CLI's current sign-in into this process (works with `aws login`)."""
    r = run(["aws", "configure", "export-credentials", "--format", "env-no-export"],
            capture_output=True, text=True)
    if r.returncode:
        return False
    for line in r.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
    return True


def sign_in():
    account = signed_in()
    if account:
        return account
    if not shutil.which("aws"):
        sys.exit("The AWS CLI is not installed. Run: winget install -e --id Amazon.AWSCLI\n"
                 "then open a new terminal and run this script again.")
    if load_cli_login() and (account := signed_in()):
        return account
    print("No valid AWS sign-in found. Opening the browser for `aws login` ...")
    if run(["aws", "login"]).returncode:
        sys.exit("`aws login` did not finish. Run it once by hand, then run this script again.")
    if load_cli_login() and (account := signed_in()):
        return account
    sys.exit("Signed in, but the credentials could not be loaded. Send the output above to the team.")


def stack_outputs():
    import boto3
    from botocore.exceptions import ClientError
    try:
        stack = boto3.client("cloudformation").describe_stacks(StackName=STACK)["Stacks"][0]
    except ClientError as e:
        sys.exit(f"Could not read {STACK} in {os.environ['AWS_REGION']}: {e}")
    return {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}


def main():
    parser = argparse.ArgumentParser(description="Build and publish the site.")
    parser.add_argument("--dry-run", action="store_true", help="build and list files, upload nothing")
    args = parser.parse_args()

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or DEFAULT_REGION
    os.environ["AWS_REGION"] = os.environ["AWS_DEFAULT_REGION"] = region

    print("=== 1/4 Build site/")
    if run([sys.executable, "scripts/build_site.py"]).returncode:
        sys.exit("Build failed; nothing was uploaded.")
    if args.dry_run:
        run([sys.executable, "scripts/publish_site.py", "--dry-run"])
        return

    ensure_boto3()
    print("\n=== 2/4 Sign in to AWS")
    print(f"signed in to account {sign_in()} ({region})")

    print("\n=== 3/4 Find the bucket and CloudFront distribution")
    out = stack_outputs()
    bucket, dist = out.get("BucketName"), out.get("DistributionId")
    if not bucket or not dist:
        sys.exit(f"{STACK} has no BucketName/DistributionId outputs: {out}")
    print(f"bucket {bucket}, distribution {dist}")

    print("\n=== 4/4 Upload and refresh CloudFront")
    r = run([sys.executable, "scripts/publish_site.py", "--bucket", bucket, "--distribution", dist])
    if r.returncode:
        sys.exit("Upload failed; see the error above.")
    print(f"\nDone. {out.get('SiteUrl', 'The site')} updates in a minute or two.")


if __name__ == "__main__":
    main()
