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
        setError(err instanceof Error ? err.message : "Failed to load related plants");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [query, basis]);

  return (
    <section className="rounded-3xl border bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-neutral-950">
            {SECTION_LABELS[basis] || basis}
          </h2>
          <p className="text-sm text-neutral-500">
            {loading
              ? "Loading..."
              : `${plants.length} result${plants.length === 1 ? "" : "s"}`}
            {cacheHit !== null && <span> · cache {cacheHit ? "hit" : "miss"}</span>}
            {duration !== null && <span> · {duration}s</span>}
          </p>
        </div>
      </div>

      {loading && (
        <div className="rounded-2xl bg-neutral-50 p-5 text-sm text-neutral-500">
          Loading related plants...
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && warnings.length > 0 && plants.length === 0 && (
        <div className="rounded-2xl bg-neutral-50 p-5 text-sm text-neutral-500">
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