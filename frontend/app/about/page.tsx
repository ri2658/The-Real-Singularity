import Link from "next/link";
import ApiPlayground from "@/components/ApiPlayground";

export const metadata = {
  title: "How PlantDex is built — PlantDex",
  description:
    "System architecture, AWS APIs, and how PlantDex works as a discovery UI over Trefle.",
};

function ArchDiagram() {
  return (
    <div className="overflow-x-auto rounded-sm border border-border-plant bg-parchment p-6">
      <div className="mx-auto flex min-w-[40rem] flex-col items-stretch gap-4">
        <Box
          title="Browser"
          subtitle="Next.js on Vercel"
          items={[
            "Search / profiles / compare",
            "Native-range globe (Photon)",
            "Report & correction forms",
          ]}
          tone="forest"
        />
        <Arrow label="HTTPS · NEXT_PUBLIC_PLANTDEX_API_URL" />
        <Box
          title="API Gateway"
          subtitle="AWS HTTP API"
          items={[
            "GET /search · /plants/{slug} · /similar",
            "POST /plants/{slug}/report · /corrections",
          ]}
          tone="canopy"
        />
        <Arrow label="Lambda integration" />
        <div className="grid gap-4 md:grid-cols-3">
          <Box
            title="Lambda"
            subtitle="Python 3.12"
            items={[
              "Normalize Trefle payloads",
              "Similarity querying",
              "Proxy writes to Trefle",
            ]}
            tone="fern"
          />
          <Box
            title="DynamoDB"
            subtitle="Response cache + TTL"
            items={["Search / profile / similar keys", "Cuts repeat Trefle calls"]}
            tone="mist"
          />
          <Box
            title="Secrets Manager"
            subtitle="plantdex/trefle-token"
            items={["Trefle API token", "Never sent to the browser"]}
            tone="mist"
          />
        </div>
        <Arrow label="Outbound plant data" />
        <Box
          title="Trefle API"
          subtitle="trefle.io"
          items={[
            "Community-sourced plant metadata",
            "Source of truth for PlantDex",
          ]}
          tone="forest"
        />
      </div>
    </div>
  );
}

function Box({
  title,
  subtitle,
  items,
  tone,
}: {
  title: string;
  subtitle: string;
  items: string[];
  tone: "forest" | "canopy" | "fern" | "mist";
}) {
  const tones = {
    forest: "bg-forest text-white border-forest",
    canopy: "bg-canopy text-white border-canopy",
    fern: "bg-fern text-white border-fern",
    mist: "bg-mist text-ink border-border-plant",
  };

  return (
    <div className={`rounded-sm border px-5 py-4 ${tones[tone]}`}>
      <p className="font-sans text-[10px] font-semibold uppercase tracking-[0.16em] opacity-70">
        {subtitle}
      </p>
      <h3 className="font-display mt-1 text-2xl font-light">{title}</h3>
      <ul className="mt-3 space-y-1 font-sans text-sm opacity-90">
        {items.map((item) => (
          <li key={item}>• {item}</li>
        ))}
      </ul>
    </div>
  );
}

function Arrow({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-1 py-1 text-ink-muted">
      <div className="h-6 w-px bg-border-plant" />
      <p className="font-sans text-[10px] font-semibold uppercase tracking-[0.14em]">
        {label}
      </p>
      <div className="h-6 w-px bg-border-plant" />
    </div>
  );
}

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-mist">
      <div className="border-b border-border-plant bg-parchment">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <Link
            href="/"
            className="font-sans text-sm font-medium text-fern transition-colors hover:text-canopy"
          >
            ← PlantDex
          </Link>
          <p className="font-sans text-xs font-semibold uppercase tracking-[0.16em] text-ink-muted">
            How it&apos;s built
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-12">
        <p className="mb-3 font-sans text-xs font-semibold uppercase tracking-[0.18em] text-fern">
          Architecture
        </p>
        <h1 className="font-display text-4xl font-light text-ink md:text-5xl">
          How PlantDex is put together
        </h1>
        <p className="mt-4 max-w-2xl font-sans text-base leading-relaxed text-ink-muted">
          PlantDex is a discovery index and UI layer over the Trefle plant API —
          not a social app or personal collection manager. The frontend lives on
          Vercel; the API runs on AWS (API Gateway, Lambda, DynamoDB, Secrets
          Manager) and talks to Trefle on your behalf.
        </p>

        <section className="mt-12">
          <h2 className="font-display text-3xl font-light text-ink">
            System architecture
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-ink-muted">
            Requests flow browser → API Gateway → Lambda. Reads hit a DynamoDB
            cache when possible; the Trefle token never leaves Secrets Manager /
            Lambda.
          </p>
          <div className="mt-6">
            <ArchDiagram />
          </div>
        </section>

        <section className="mt-14">
          <h2 className="font-display text-3xl font-light text-ink">
            What each layer does
          </h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <article className="rounded-sm border border-border-plant bg-parchment p-5">
              <h3 className="font-display text-xl font-light text-ink">Frontend</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                Next.js App Router UI for search, profiles, related plants,
                compare (localStorage tray only), distribution globe via Photon
                geocoding, and Trefle feedback forms.
              </p>
            </article>
            <article className="rounded-sm border border-border-plant bg-parchment p-5">
              <h3 className="font-display text-xl font-light text-ink">Backend</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                Python Lambda package in <code className="text-ink">src/</code>{" "}
                normalizes Trefle payloads, runs similarity helpers, caches
                responses, and proxies report/correction writes.
              </p>
            </article>
            <article className="rounded-sm border border-border-plant bg-parchment p-5">
              <h3 className="font-display text-xl font-light text-ink">Caching</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                DynamoDB stores JSON responses keyed by request shape with TTL,
                which keeps Trefle traffic down and makes profile related-plant
                sections feel snappier on repeat views.
              </p>
            </article>
            <article className="rounded-sm border border-border-plant bg-parchment p-5">
              <h3 className="font-display text-xl font-light text-ink">Data source</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                Trefle is community-sourced and imperfect. PlantDex surfaces that
                clearly and lets users send reports/corrections upstream without
                handling API tokens in the browser.
              </p>
            </article>
          </div>
        </section>

        <ApiPlayground />
      </div>
    </main>
  );
}
