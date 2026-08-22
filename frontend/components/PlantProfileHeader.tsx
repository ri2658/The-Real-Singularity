"use client";

import { useEffect, useState } from "react";
import type { PlantProfile } from "@/lib/api";
import {
  COMPARE_MAX,
  addToCompare,
  isInCompare,
  removeFromCompare,
} from "@/lib/compare";

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Unknown";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "Unknown";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export default function PlantProfileHeader({ plant }: { plant: PlantProfile }) {
  const name = plant.common_name || plant.scientific_name || "Unknown plant";
  const slug = plant.slug || "";
  const [inCompare, setInCompare] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    function sync() {
      if (!slug) return;
      setInCompare(isInCompare(slug));
    }
    sync();
    window.addEventListener("plantdex:compare-updated", sync);
    return () => window.removeEventListener("plantdex:compare-updated", sync);
  }, [slug]);

  function toggleCompare() {
    if (!slug) return;

    if (inCompare) {
      removeFromCompare(slug);
      setMessage("Removed from compare");
      return;
    }

    const result = addToCompare({
      slug,
      common_name: plant.common_name,
      scientific_name: plant.scientific_name,
      image_url: plant.image_url,
    });

    if (result.ok) {
      setMessage("Added to compare");
      return;
    }

    if (result.reason === "full") {
      setMessage(`Compare is full (${COMPARE_MAX} max). Remove one first.`);
      return;
    }

    if (result.reason === "duplicate") {
      setMessage("Already in compare");
    }
  }

  return (
    <section className="grid gap-6 md:grid-cols-[380px_1fr]">
      <div className="overflow-hidden rounded-sm border border-border-plant bg-parchment">
        <div className="aspect-square">
          {plant.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={plant.image_url}
              alt={name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <span className="font-display italic text-ink-muted opacity-40">
                No specimen image
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col justify-between rounded-sm border border-border-plant bg-parchment p-8">
        <div>
          <p className="mb-3 font-sans text-xs font-semibold uppercase tracking-[0.18em] text-fern">
            Plant profile
          </p>

          <h1 className="font-display text-5xl font-light leading-tight text-ink">
            {name}
          </h1>

          <p className="font-display mt-2 text-xl font-light italic text-ink-muted">
            {plant.scientific_name || "Scientific name unavailable"}
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={toggleCompare}
              disabled={!slug}
              className={`rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors ${
                inCompare
                  ? "border border-fern bg-mist text-fern hover:bg-leaf/30"
                  : "bg-fern text-white hover:bg-canopy"
              } disabled:cursor-not-allowed disabled:opacity-50`}
            >
              {inCompare ? "Remove from compare" : "Add to compare"}
            </button>
            {message && (
              <span className="text-sm text-ink-muted">{message}</span>
            )}
          </div>

          <div className="my-7 h-px bg-border-plant" />

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Info label="Genus" value={plant.genus} />
            <Info label="Family" value={plant.family} />
            <Info label="Edible" value={formatValue(plant.edible)} />
            <Info
              label="Growth habit"
              value={
                plant.specifications &&
                typeof plant.specifications === "object"
                  ? (plant.specifications as Record<string, unknown>).growth_habit
                  : null
              }
            />
            <Info
              label="Growth form"
              value={
                plant.specifications &&
                typeof plant.specifications === "object"
                  ? (plant.specifications as Record<string, unknown>).growth_form
                  : null
              }
            />
            <Info label="Vegetable" value={formatValue(plant.vegetable)} />
          </div>

          <p className="mt-6 text-sm text-ink-muted">
            Full taxonomy, traits, growth data, and native range map are below.
          </p>
        </div>
      </div>
    </section>
  );
}

function Info({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="border-l-2 border-border-plant pl-3">
      <div className="font-sans text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
        {label}
      </div>
      <div className="mt-0.5 font-sans text-sm font-medium text-ink">
        {formatValue(value)}
      </div>
    </div>
  );
}
