# PlantDex Design Document

## Overview

PlantDex is a plant discovery website: an online index and UI layer over the [Trefle](https://trefle.io) plant API. It helps users search for familiar plants and explore related species, lesser-known relatives, and similar plants through taxonomy and trait-based discovery.

Instead of identifying a plant from a photo or managing a personal garden list, PlantDex focuses on botanical context. For example, searching “blueberry” can surface bilberries, lingonberries, cranberries, and other plants in the *Vaccinium* genus or Ericaceae family.

This is not primarily a machine learning project. The product is a read-mostly discovery interface: search, profiles, related plants, compare, distribution visualization, short AI overviews, and lightweight tooling to report or correct upstream Trefle data.

## Customer Identification & Problem Statement

The target users are gardeners, students, plant hobbyists, educators, and curious users who want to learn more about plants beyond a single common name. Many people know broad plant names like “blueberry,” “maple,” or “monstera,” but they may not realize that each name can refer to many species, cultivars, or related plants. This is especially clear with rare species and translated common names that map to related but non-identical species (e.g. custard apple — *Annona reticulata* vs sugar apple — *Annona squamosa*).

Existing plant tools often focus on image identification, care reminders, or shopping. They usually do not make it easy to explore botanical relationships in an accessible way. Users want answers like: What species are related to this plant? Are there lesser-known edible relatives? What shares this genus, family, or fruit color? How do similar plants compare?

A successful outcome is a deployed website where users can search a plant, open a rich profile, discover related plants, compare them side by side, skim an AI overview keyed to the scientific name, and optionally contribute corrections back to Trefle.

## Background Research and Related Work

Related tools and concepts include:

- Trefle API for plant taxonomy and metadata
- USDA PLANTS Database, GBIF, and iNaturalist-style biodiversity databases
- Plant identification apps such as PictureThis or PlantNet
- Rule-based recommendation / similarity systems based on metadata matching
- Generative AI for short explanatory copy (not for inventing citations or care advice)

PlantDex differs by treating Trefle as the source of truth and providing a polished discovery UX on top of it, rather than building a social save/collections product or a diagnostic app.

## Goals

1. Allow users to search for plants by common or scientific name, with paginated “load more” up to a safe cap.
2. Display plant results as clean image cards with names and key metadata.
3. Provide detailed plant profile pages with taxonomy, traits, distribution, and a globe for native **and** introduced ranges when data exists.
4. Recommend related plants using taxonomy and metadata-based similarity (genus, family, distribution, edible part, growth habit, fruit color, etc.).
5. Let users compare 2–4 plants side by side.
6. Offer short AI-generated overviews on search result sets and individual profiles (summary text only; disclaimer that AI is imperfect).
7. Cache Trefle responses to reduce repeated external API calls.
8. Deploy the backend on AWS and the frontend on Vercel (with Web Analytics).
9. Allow users to report errors or submit corrections to Trefle through PlantDex (token stays server-side).

## Non-Goals

PlantDex deliberately does **not** include:

1. User accounts, authentication, or personal plant collections.
2. Guaranteed local growing recommendations by ZIP code.
3. Cultivar recommendations for a user’s climate.
4. Disease diagnosis or computer-vision identification.
5. Professional agricultural or horticultural advice.
6. Marketplace / nursery inventory.
7. Training a custom machine learning model.
8. Fully verifying all Trefle data manually.
9. AI-invented citations, tasting-video links, or “source lists” presented as verified references.

Collections and auth were considered in an earlier draft and rejected: the practical value of PlantDex is discovery indexing over Trefle, not becoming an active save/social product.

## System Architecture

```mermaid
flowchart LR
  User[Browser / Vercel frontend] -->|HTTPS| APIGW[API Gateway HTTP API]
  APIGW --> Lambda[Python Lambda]
  Lambda -->|cache read/write| DDB[DynamoDB cache]
  Lambda -->|read token| SM[Secrets Manager]
  Lambda -->|plant search / details / filters| Trefle[Trefle API]
  User -->|Photon geocoding for globe| Photon[Photon / OSM]
  User -->|report / correction via Lambda| Trefle
  User -->|AI summary via Next.js route| OpenAI[OpenAI API]
```

- **Frontend (Next.js on Vercel):** search UI (load more), plant profiles, AI overview cards, related-plant sections, compare tray/page, distribution globe (native + introduced), about/architecture page with API playground, Trefle feedback forms, Vercel Analytics.
- **Backend (AWS):** API Gateway → Lambda handlers in `src/`. Secrets Manager holds the Trefle token. DynamoDB caches search/profile/similar responses with TTL. Search paginates Trefle and returns `has_more` (cap 100).
- **AI (Vercel server routes):** `POST /api/ai/search-summary` and `POST /api/ai/plant-summary` call OpenAI with `OPENAI_API_KEY` (server-only). Profiles key botanical identity on the **scientific name**. Output is summary text only plus an accuracy disclaimer in the UI.
- **External:** Trefle for plant data; Photon (OpenStreetMap) for geocoding distribution place names; OpenAI for overview copy.

## Data Sources

The primary botanical data source is the Trefle API (common names, scientific names, taxonomy, images, distribution, growth traits). PlantDex does not maintain its own botanical database beyond short-lived API response caches.

Cached responses in DynamoDB are keyed by request shape (e.g. search query + `max_results`, plant slug, similarity basis) and expire via TTL.

Known data issues: missing images, incomplete traits, inconsistent common names, Trefle typos, and limited cultivar-level data. The UI uses fallbacks, null-safe rendering, disclaimers, AI-overview caveats, and Trefle report/correction flows.

## PlantDex Backend API

Base URL is the deployed API Gateway endpoint (`NEXT_PUBLIC_PLANTDEX_API_URL` on the frontend).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/search` | Search plants by query (paginated Trefle pages; `has_more`) |
| `GET` | `/plants/{slug}` | Full plant profile |
| `GET` | `/similar` | Related plants by basis |
| `POST` | `/plants/{slug}/report` | Proxy error report to Trefle |
| `POST` | `/plants/{slug}/corrections` | Proxy field correction to Trefle |

### Frontend-only AI routes (Next.js on Vercel)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/ai/search-summary` | Short AI summary of a search result set |
| `POST` | `/api/ai/plant-summary` | Short AI overview for one plant profile |

These routes never receive the Trefle token; they use `OPENAI_API_KEY` on the Vercel/Node runtime only.

### `GET /search`

Query params: `query` (required), `max_results` (clamped, default 12, max 100), `image_only`.

Returns normalized plant cards plus `count`, `has_more`, `warnings`, and cache metadata. The UI loads 12 at a time and offers **Load more** while `has_more` is true.

### `GET /plants/{slug}`

Returns `{ slug, plant, warnings, cache }` where `plant` includes taxonomy, traits (`flower`, `foliage`, `fruit_or_seed`, `specifications`, `growth`), distribution, and a `raw` Trefle payload for richer UI fields.

### `GET /similar`

Query params: `query`, `basis` (`genus` \| `family` \| `distribution` \| `edible_part` \| `growth_habit` \| `growth_form` \| `fruit_color` \| `bundle`), `max_results` (capped lower than search), `image_only`.

Returns related plant cards, warnings when a trait is missing, timing, and cache metadata.

### `POST /plants/{slug}/report`

Body: `{ notes, species_id? }`. Proxies to Trefle’s species report endpoint using the server-side token.

### `POST /plants/{slug}/corrections`

Body: `{ notes?, source_type, source_reference, correction, species_id? }`. Proxies to Trefle’s species correction endpoint with an allowlisted set of fields.

## Execution Flow

1. User visits PlantDex (Vercel).
2. User searches for a plant (e.g. “blueberry”).
3. Frontend calls `GET /search` (12 results); may call again with a larger `max_results` on **Load more**.
4. Lambda checks DynamoDB cache; on miss, pages Trefle until the window is filled or pages run out, normalizes cards, caches, returns results + `has_more`.
5. Frontend requests an AI search summary (summary text only) via `/api/ai/search-summary`.
6. User opens a profile → `GET /plants/{slug}`; AI plant overview via `/api/ai/plant-summary` (scientific-name keyed); Overview + distribution (native/introduced chips + globe); related sections via concurrent `GET /similar` (client-limited).
7. User may add plants to a local compare tray (browser storage only) and open `/compare`.
8. User may report an error or submit a correction; Lambda forwards to Trefle without exposing the API token.

## Security and Configuration

```env
# Backend / Lambda
TREFLE_TOKEN=...                    # local only
TREFLE_SECRET_NAME=plantdex/trefle-token
CACHE_TABLE_NAME=...

# Frontend (Vercel / .env.local)
NEXT_PUBLIC_PLANTDEX_API_URL=https://....execute-api.us-west-2.amazonaws.com
OPENAI_API_KEY=...                  # server-only; never NEXT_PUBLIC_
# OPENAI_MODEL=gpt-4o-mini          # optional
```

Practices:

- Keep the Trefle token in AWS Secrets Manager; never ship it to the browser.
- Keep the OpenAI key in Vercel env / local `.env.local` for Next.js API routes only (not Secrets Manager unless AI is moved onto Lambda later).
- Proxy Trefle writes (report/correction) through Lambda.
- Validate inputs and allowlist correction fields.
- Cache repeated reads; limit concurrent `/similar` requests from the client; raise Lambda timeout for multi-page search / similar bursts.
- Use SSO for AWS ops (`aws sso login --profile plantdex`).
- Vercel: Root Directory = `frontend`; Production Branch = `main`.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Trefle data incomplete or wrong | Fallback UI, disclaimer, report/correction forms |
| Trefle rate limits / latency | DynamoDB cache, Lambda timeout headroom, client concurrency limits + retries, search pagination cap |
| Vague searches (“berry”, “tree”) | Ranked results, example queries, load-more instead of dumping hundreds |
| API key exposure | Backend-only Trefle calls; Secrets Manager; OpenAI key server-only on Vercel |
| AI overview inaccuracy | Summary-only (no fake citations); UI disclaimer; scientific-name keyed prompts |
| Scope creep into auth/collections/climate tools | Explicit non-goals; stay a discovery UI over Trefle |

## Rollout Plan

### Phase 1 — Search and profiles ✅

Frontend search + plant profiles; backend Trefle integration; DynamoDB caching.

### Phase 2 — Related plant discovery ✅

Similarity by genus, family, distribution, edible part, growth habit/form, fruit color.

### Phase 3 — Compare ✅

Select 2–4 plants and compare taxonomy/traits side by side (local tray; no accounts).

### Phase 4 — Cloud deployment ✅

- Backend: AWS Lambda + API Gateway + Secrets Manager + DynamoDB
- Frontend: Vercel (Root Directory `frontend`, production from `main`, Web Analytics)
- About/architecture page + interactive API playground (GET live; report/corrections example-only)

### Phase 5 — AI overviews + discovery polish ✅ / ongoing

- AI search + profile summaries (text only) via Next.js + OpenAI
- Search load-more with Trefle pagination (`has_more`, max 100)
- Native + introduced distribution globe with color legend

### Optional future extensions

Stronger filters/autocomplete, curated discovery paths, richer maps — still without requiring user accounts unless a future product decision revisits that explicitly.
