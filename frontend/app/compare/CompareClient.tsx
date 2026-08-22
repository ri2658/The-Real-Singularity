"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  COMPARE_MAX,
  COMPARE_MIN,
  clearCompare,
  getCompareList,
  parseCompareSlugs,
  removeFromCompare,
} from "@/lib/compare";
import { getPlantProfile, type PlantProfile } from "@/lib/api";

type LoadedPlant = {
  slug: string;
  plant: PlantProfile | null;
  error?: string;
};

const ROWS: { key: string; label: string; get: (p: PlantProfile) => unknown }[] = [
  { key: "common_name", label: "Common name", get: (p) => p.common_name },
  { key: "scientific_name", label: "Scientific name", get: (p) => p.scientific_name },
  { key: "genus", label: "Genus", get: (p) => p.genus },
  { key: "family", label: "Family", get: (p) => p.family },
  { key: "family_common_name", label: "Family common name", get: (p) => p.family_common_name },
  { key: "edible", label: "Edible", get: (p) => p.edible },
  { key: "edible_part", label: "Edible part", get: (p) => p.edible_part },
  { key: "vegetable", label: "Vegetable", get: (p) => p.vegetable },
  { key: "duration", label: "Duration", get: (p) => p.duration },
  {
    key: "distribution",
    label: "Native distribution",
    get: (p) => {
      const dist = p.distribution || p.distributions;
      if (!dist || typeof dist !== "object") return null;
      return (dist as Record<string, unknown>).native;
    },
  },
];

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function ComparePage() {
  const searchParams = useSearchParams();
  const plantsParam = searchParams.get("plants");

  const slugs = useMemo(() => {
    const fromQuery = parseCompareSlugs(plantsParam);
    if (fromQuery.length) return fromQuery;
    return getCompareList()
      .map((p) => p.slug)
      .slice(0, COMPARE_MAX);
  }, [plantsParam]);

  const [rows, setRows] = useState<LoadedPlant[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!slugs.length) {
        setRows([]);
        return;
      }

      setLoading(true);
      const results = await Promise.all(
        slugs.map(async (slug) => {
          try {
            const data = await getPlantProfile(slug);
            return { slug, plant: data.plant } satisfies LoadedPlant;
          } catch (err) {
            return {
              slug,
              plant: null,
              error: err instanceof Error ? err.message : "Failed to load",
            } satisfies LoadedPlant;
          }
        })
      );

      if (!cancelled) {
        setRows(results);
        setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [slugs]);

  function handleRemove(slug: string) {
    removeFromCompare(slug);
    setRows((prev) => prev.filter((row) => row.slug !== slug));
  }

  return (
    <main className="min-h-screen bg-mist pb-28">
      <div className="border-b border-border-plant bg-parchment">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <Link
            href="/"
            className="font-sans text-sm font-medium text-fern transition-colors hover:text-canopy"
          >
            ← PlantDex
          </Link>
          {rows.length > 0 && (
            <button
              type="button"
              onClick={() => {
                clearCompare();
                setRows([]);
              }}
              className="text-sm text-ink-muted transition-colors hover:text-ink"
            >
              Clear compare
            </button>
          )}
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="mb-2 font-sans text-xs font-semibold uppercase tracking-[0.18em] text-fern">
          Compare
        </p>
        <h1 className="font-display text-4xl font-light text-ink md:text-5xl">
          Compare plants
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-ink-muted">
          Select {COMPARE_MIN}–{COMPARE_MAX} plants from profile pages, then compare taxonomy,
          edibility, and distribution side by side.
        </p>

        {!slugs.length && (
          <div className="mt-10 rounded-sm border border-border-plant bg-parchment p-10 text-center">
            <p className="font-display text-2xl font-light italic text-ink-muted">
              No plants selected yet
            </p>
            <p className="mt-2 text-sm text-ink-muted">
              Open a plant profile and tap “Add to compare”.
            </p>
            <Link
              href="/"
              className="mt-6 inline-flex rounded-lg bg-fern px-5 py-2.5 text-sm font-semibold text-white hover:bg-canopy"
            >
              Search plants
            </Link>
          </div>
        )}

        {slugs.length > 0 && slugs.length < COMPARE_MIN && (
          <div className="mt-6 rounded-sm border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            Add at least {COMPARE_MIN - slugs.length} more plant
            {COMPARE_MIN - slugs.length === 1 ? "" : "s"} to compare.
          </div>
        )}

        {loading && (
          <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {slugs.map((slug) => (
              <div
                key={slug}
                className="aspect-[3/4] rounded-sm border border-border-plant bg-parchment shimmer"
              />
            ))}
          </div>
        )}

        {!loading && rows.length > 0 && (
          <div className="mt-10 overflow-x-auto rounded-sm border border-border-plant bg-parchment">
            <table className="min-w-full table-fixed border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border-plant">
                  <th className="sticky left-0 z-10 w-40 bg-parchment px-4 py-4 font-sans text-xs font-semibold uppercase tracking-widest text-ink-muted">
                    Trait
                  </th>
                  {rows.map((row) => {
                    const name =
                      row.plant?.common_name ||
                      row.plant?.scientific_name ||
                      row.slug;
                    return (
                      <th key={row.slug} className="w-56 px-4 py-4 align-top">
                        <div className="space-y-3">
                          {/* Fixed box: table cells ignore aspect-ratio and size to intrinsic image dims */}
                          <div className="relative h-40 w-full overflow-hidden rounded-sm border border-border-plant bg-mist">
                            {row.plant?.image_url ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={row.plant.image_url}
                                alt={name}
                                className="absolute inset-0 block h-full w-full object-cover"
                              />
                            ) : (
                              <div className="absolute inset-0 flex items-center justify-center text-xs italic text-ink-muted">
                                No image
                              </div>
                            )}
                          </div>
                          <div>
                            <Link
                              href={`/plants/${row.slug}`}
                              className="font-display line-clamp-2 text-lg font-semibold text-ink hover:text-fern"
                            >
                              {name}
                            </Link>
                            <p className="font-display line-clamp-2 text-sm italic text-ink-muted">
                              {row.plant?.scientific_name || "—"}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemove(row.slug)}
                            className="text-xs text-ink-muted hover:text-fern"
                          >
                            Remove
                          </button>
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((trait) => (
                  <tr key={trait.key} className="border-b border-border-plant/70">
                    <th className="sticky left-0 z-10 bg-parchment px-4 py-3 font-sans text-xs font-semibold uppercase tracking-widest text-ink-muted">
                      {trait.label}
                    </th>
                    {rows.map((row) => (
                      <td key={`${row.slug}-${trait.key}`} className="px-4 py-3 text-ink">
                        {row.error
                          ? row.error
                          : row.plant
                            ? formatValue(trait.get(row.plant))
                            : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
