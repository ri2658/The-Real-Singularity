# PlantDex

Plant discovery UI over the [Trefle](https://trefle.io) API — search, profiles, related plants, compare, and native-range visualization. No user accounts or personal collections.

See [`DesignDoc.md`](./DesignDoc.md) for product scope and architecture.

## Structure

- `frontend/` — Next.js app (Vercel)
- `src/` — Python Lambda handlers + Trefle similarity helpers
- `infrastructure/` — AWS CDK (API Gateway, Lambda, DynamoDB, Secrets Manager)
- `notebooks/` / `tests/` — exploration and notebooks

## Frontend

```bash
cd frontend
cp .env.example .env.local
# set NEXT_PUBLIC_PLANTDEX_API_URL and OPENAI_API_KEY (server-only)
npm install
npm run dev
```

Deploy to Vercel from the repo with **Root Directory** `frontend`, production branch `main`, and env vars `NEXT_PUBLIC_PLANTDEX_API_URL` + `OPENAI_API_KEY` set for Production/Preview.

## Backend

```bash
aws sso login --profile plantdex
cd infrastructure
source .venv/bin/activate
AWS_PROFILE=plantdex cdk deploy
```
