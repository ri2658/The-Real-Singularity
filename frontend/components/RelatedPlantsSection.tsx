"use client";

import { useEffect, useState } from "react";
import PlantCard from "@/components/PlantCard";
import { getSimilarPlants, type PlantCard as PlantCardType } from "@/lib/api";

const SECTION_LABELS: Record<string, string> = {
  genus: "Same genus",
  family: "Same family",
  distribution: "Same distribution",
  edible_part: "Similar edible parts",
  growth_habit: "Similar growth habit",
  growth_form: "Similar growth form",
  fruit_color: "Similar fruit color",
};

const BADGE_STYLES: Record<string, string> = {
  genus: "text-fern border-leaf/60",
  family: "text-canopy border-leaf/60",
  distribution: "text-ink-muted border-border-plant",
  edible_part: "text-fern border-border-plant",
  growth_habit: "text-ink-muted border-border-plant",
  growth_form: "text-ink-muted border-border-plant",
  fruit_color: "text-fern border-border-plant",
};

function SkeletonCard() {
  return (
    <div className="overflow-hidden rounded-sm border border-border-plant bg-parchment">
      <div className="aspect-[4/3] shimmer" />
      <div className="space-y-2 p-4">
        <div className="h-4 w-3/4 rounded shimmer" />
        <div className="h-3.5 w-1/2 rounded shimmer" />
      </div>
    </div>
  );
}

export default function RelatedPlantsSection({
  query,
  basis,
}: {
  query: string;
  basis: string;
}) {
  const [plants, setPlants] = useState<PlantCardType[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [cacheHit, setCacheHit] = useState<boolean | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const data = await getSimilarPlants({
          query,
          basis,
          maxResults: 6,
          imageOnly: false,
        });

        if (cancelled) return;

        setPlants(data.results || []);
        setWarnings(data.warnings || []);
        setCacheHit(data.cache?.hit ?? null);
        setDuration(data.timing?.duration_seconds ?? null);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Failed to load related plants"
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [query, basis]);

  const badgeStyle = BADGE_STYLES[basis] ?? BADGE_STYLES.genus;

  return (
    <section className="rounded-sm border border-border-plant bg-parchment p-6">
      <div className="mb-5 flex items-start gap-3">
        <span
          className={`mt-0.5 shrink-0 rounded-full border bg-mist px-2.5 py-0.5 font-sans text-xs font-semibold uppercase tracking-wider ${badgeStyle}`}
        >
          {basis.replace("_", " ")}
        </span>
        <div>
          <h2 className="font-display text-xl font-light text-ink">
            {SECTION_LABELS[basis] || basis}
          </h2>
          <p className="mt-0.5 font-sans text-xs text-ink-muted">
            {loading ? (
              "Finding related plants…"
            ) : (
              <>
                {plants.length} species
                {cacheHit !== null && (
                  <span> · cache {cacheHit ? "hit" : "miss"}</span>
                )}
                {duration !== null && <span> · {duration}s</span>}
              </>
            )}
          </p>
        </div>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-sm border border-red-200 bg-red-50 p-4 font-sans text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && warnings.length > 0 && plants.length === 0 && (
        <div className="rounded-sm border border-border-plant p-4 font-sans text-sm text-ink-muted">
          {warnings.join(" ")}
        </div>
      )}

      {!loading && plants.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {plants.map((plant) => (
            <PlantCard
              key={plant.slug || plant.id || plant.scientific_name}
              plant={plant}
            />
          ))}
        </div>
      )}
    </section>
  );
}
