"use client";

import { useState } from "react";
import SearchBar from "@/components/SearchBar";
import PlantCard from "@/components/PlantCard";
import { searchPlants, type PlantCard as PlantCardType } from "@/lib/api";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [plants, setPlants] = useState<PlantCardType[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [cacheHit, setCacheHit] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(nextQuery: string) {
    setQuery(nextQuery);
    setLoading(true);
    setError("");
    setWarnings([]);
    setCacheHit(null);

    try {
      const data = await searchPlants({
        query: nextQuery,
        maxResults: 12,
        imageOnly: false,
      });

      setPlants(data.results || []);
      setWarnings(data.warnings || []);
      setCacheHit(data.cache?.hit ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setPlants([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-neutral-50">
      <section className="mx-auto flex max-w-6xl flex-col items-center px-6 py-16 text-center">
        <div className="mb-8 max-w-3xl">
          <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-green-700">
            PlantDex
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-neutral-950 md:text-6xl">
            Discover what your favorite plants are connected to.
          </h1>
          <p className="mt-5 text-lg text-neutral-600">
            Search a familiar plant, open its profile, and explore related
            species by genus, family, distribution, and traits.
          </p>
        </div>

        <SearchBar onSearch={handleSearch} />

        <div className="mt-4 flex gap-2 text-sm text-neutral-500">
          <button onClick={() => handleSearch("blueberry")} className="hover:text-green-700">
            blueberry
          </button>
          <span>·</span>
          <button onClick={() => handleSearch("tomato")} className="hover:text-green-700">
            tomato
          </button>
          <span>·</span>
          <button onClick={() => handleSearch("monstera")} className="hover:text-green-700">
            monstera
          </button>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-16">
        {loading && (
          <div className="rounded-2xl border bg-white p-6 text-neutral-600">
            Searching PlantDex...
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-700">
            {error}
          </div>
        )}

        {!loading && query && !error && (
          <div className="mb-6 flex items-end justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-neutral-950">
                Results for “{query}”
              </h2>
              <p className="text-sm text-neutral-500">
                {plants.length} result{plants.length === 1 ? "" : "s"}
                {cacheHit !== null && (
                  <span> · cache {cacheHit ? "hit" : "miss"}</span>
                )}
              </p>
            </div>
          </div>
        )}

        {warnings.length > 0 && (
          <div className="mb-6 rounded-2xl border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
            {warnings.join(" ")}
          </div>
        )}

        {plants.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {plants.map((plant) => (
              <PlantCard
                key={plant.slug || plant.id || plant.scientific_name}
                plant={plant}
              />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}