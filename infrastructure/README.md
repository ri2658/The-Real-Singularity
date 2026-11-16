# Infra

AWS CDK stack that hosts the site: a private S3 bucket behind CloudFront (`burgers_site_stack.py`, created from `site_app.py`).

## One-time setup

```bash
cd infrastructure
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install -g aws-cdk
cdk bootstrap
cdk deploy BurgersSiteStack
```

The stack outputs `BucketName`, `DistributionId` and `SiteUrl`.

## Publishing updates

From the repo root, pass the bucket and distribution from the stack outputs:

```bash
python scripts/build_site.py
python scripts/publish_site.py --bucket BUCKET --distribution DIST_ID
```
