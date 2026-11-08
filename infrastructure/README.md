# Infra

AWS CDK stack for the PlantDex backend (Lambda + HTTP API + DynamoDB cache + Secrets Manager).

## Deploy

Use the SSO profile (do not use long-lived access keys):

```bash
aws sso login --profile plantdex
cd infrastructure
source .venv/bin/activate
AWS_PROFILE=plantdex cdk deploy
```

This stack is the PlantDex API only. It does not serve the Burgers page. That site is `burgers_site_stack.py`, deployed with `site_app.py`. Steps are in [`../web/README.md`](../web/README.md).

After deploy, set the frontend env var to the stack output `PlantDexApiUrl`:

```bash
# frontend/.env.local
NEXT_PUBLIC_PLANTDEX_API_URL=https://....execute-api.us-west-2.amazonaws.com
```
