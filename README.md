# PlantDex

PlantDex is a plant **discovery** site built as a UI and index over the [Trefle](https://trefle.io) plant API. Search a familiar common name (or a scientific one), open rich species profiles, explore related plants by taxonomy and traits, compare a few side by side, and skim a short AI overview — without accounts or personal collections.

The product goal is botanical context, not identification from photos or garden tracking. Searching “blueberry,” for example, should help you see related *Vaccinium* species and Ericaceae relatives, not just a single shopping card.

See [`DesignDoc.md`](./DesignDoc.md) for full product scope, API surface, and architecture.

## What you can do

- **Search** plants by common or scientific name, with paginated “load more” results
- **Profiles** with taxonomy, traits, distribution chips, and a globe for native + introduced ranges
- **Related discovery** by genus, family, distribution, edible part, growth habit, fruit color, and more
- **Compare** 2–4 plants in a local tray / compare page (browser storage only)
- **AI overviews** (summary text) on search results and profiles — imperfect; treat as a starting point
- **Report / correct** Trefle data through the app (API token stays on the server)

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

Deploy on Vercel with:

- **Root Directory:** `frontend`
- **Production branch:** `main`
- **Env:** `NEXT_PUBLIC_PLANTDEX_API_URL` and `OPENAI_API_KEY` (Production + Preview; never `NEXT_PUBLIC_` for the OpenAI key)

## Backend

```bash
aws sso login --profile plantdex
cd infrastructure
source .venv/bin/activate
AWS_PROFILE=plantdex cdk deploy
```

The Lambda stack proxies Trefle reads/writes, caches responses in DynamoDB, and keeps the Trefle token in Secrets Manager.
