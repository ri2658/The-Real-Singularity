"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { PlantProfile } from "@/lib/api";
import { extractDistributionNames } from "@/lib/geo";

const DistributionGlobe = dynamic(() => import("./DistributionGlobe"), {
  ssr: false,
  loading: () => (
    <div className="h-[360px] animate-pulse rounded-sm border border-border-plant bg-[#0b1a12]" />
  ),
});

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) {
    if (!value.length) return "—";
    return value
      .map((item) => {
        if (item && typeof item === "object" && "name" in item) {
          return String((item as { name: unknown }).name);
        }
        return formatValue(item);
      })
      .join(", ");
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(
      ([, v]) => v !== null && v !== undefined && v !== ""
    );
    if (!entries.length) return "—";
    if (
      entries.length <= 3 &&
      entries.every(([, v]) => typeof v === "number" || typeof v === "string")
    ) {
      return entries.map(([k, v]) => `${v} ${k}`).join(" · ");
    }
    return entries
      .map(([k, v]) => `${humanizeKey(k)}: ${formatValue(v)}`)
      .join(" · ");
  }
  return String(value);
}

function humanizeKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function hasDisplayable(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") {
    return Object.values(value as Record<string, unknown>).some(hasDisplayable);
  }
  return true;
}

function flattenObject(
  obj: Record<string, unknown> | null | undefined,
  prefix = ""
): { label: string; value: unknown }[] {
  if (!obj) return [];
  const rows: { label: string; value: unknown }[] = [];

  for (const [key, value] of Object.entries(obj)) {
    const label = prefix ? `${prefix} · ${humanizeKey(key)}` : humanizeKey(key);

    if (value && typeof value === "object" && !Array.isArray(value)) {
      const nested = value as Record<string, unknown>;
      const nestedEntries = Object.entries(nested).filter(([, v]) =>
        hasDisplayable(v)
      );

      if (
        nestedEntries.length > 0 &&
        nestedEntries.length <= 3 &&
        nestedEntries.every(
          ([, v]) => typeof v === "number" || typeof v === "string"
        )
      ) {
        rows.push({ label, value: nested });
      } else if (nestedEntries.length) {
        rows.push(...flattenObject(nested, label));
      }
      continue;
    }

    if (hasDisplayable(value)) {
      rows.push({ label, value });
    }
  }

  return rows;
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-sm border border-border-plant bg-parchment p-6">
      <h3 className="font-display text-2xl font-light text-ink">{title}</h3>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function FieldGrid({ rows }: { rows: { label: string; value: unknown }[] }) {
  if (!rows.length) {
    return <p className="text-sm text-ink-muted">No data available.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {rows.map((row) => (
        <div key={row.label} className="border-l-2 border-border-plant pl-3">
          <div className="font-sans text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
            {row.label}
          </div>
          <div className="mt-0.5 font-sans text-sm font-medium text-ink">
            {formatValue(row.value)}
          </div>
        </div>
      ))}
    </div>
  );
}

function ChipList({
  items,
  initialVisible = 0,
}: {
  items: string[];
  /** When > 0, show this many chips first with a View more control */
  initialVisible?: number;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!items.length) {
    return <p className="text-sm text-ink-muted">None listed.</p>;
  }

  const collapsible = initialVisible > 0 && items.length > initialVisible;
  const visible =
    !collapsible || expanded ? items : items.slice(0, initialVisible);
  const hiddenCount = items.length - initialVisible;

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {visible.map((item) => (
          <span
            key={item}
            className="rounded-full border border-border-plant bg-mist px-3 py-1 text-xs font-medium text-ink"
          >
            {item}
          </span>
        ))}
      </div>
      {collapsible && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-3 text-xs font-semibold text-fern transition-colors hover:text-canopy"
        >
          {expanded ? "Show less" : `View more (${hiddenCount})`}
        </button>
      )}
    </div>
  );
}

export default function PlantProfileDetails({ plant }: { plant: PlantProfile }) {
  const raw = (plant.raw || {}) as Record<string, unknown>;
  const mainSpecies = (raw.main_species || {}) as Record<string, unknown>;

  const overviewRows = [
    { label: "Genus", value: plant.genus },
    { label: "Family", value: plant.family },
    { label: "Family common name", value: plant.family_common_name },
    { label: "Edible", value: plant.edible },
    { label: "Edible part", value: plant.edible_part },
    { label: "Vegetable", value: plant.vegetable },
    { label: "Duration", value: plant.duration || mainSpecies.duration },
    { label: "Rank", value: mainSpecies.rank },
    { label: "Status", value: mainSpecies.status },
    { label: "Year", value: mainSpecies.year },
    { label: "Author", value: mainSpecies.author },
    { label: "Observations", value: mainSpecies.observations },
    ...flattenObject(plant.flower || undefined, "Flower"),
    ...flattenObject(plant.foliage || undefined, "Foliage"),
    ...flattenObject(plant.fruit_or_seed || undefined, "Fruit / seed"),
    ...flattenObject(plant.specifications || undefined),
    ...flattenObject(plant.growth || undefined, "Growth"),
  ].filter((row) => hasDisplayable(row.value));

  const synonymNames = Array.isArray(mainSpecies.synonyms)
    ? mainSpecies.synonyms
        .map((s) => {
          if (typeof s === "string") return s;
          if (s && typeof s === "object" && "name" in s) {
            return String((s as { name: unknown }).name);
          }
          return "";
        })
        .filter(Boolean)
    : [];

  const native = extractDistributionNames(plant.distribution, "native");
  const introduced = extractDistributionNames(plant.distribution, "introduced");

  const nativeFallback =
    native.length > 0
      ? native
      : extractDistributionNames(
          (plant.distributions as Record<string, unknown>) || null,
          "native"
        );
  const introducedFallback =
    introduced.length > 0
      ? introduced
      : extractDistributionNames(
          (plant.distributions as Record<string, unknown>) || null,
          "introduced"
        );

  return (
    <div className="mt-10 space-y-6">
      <Section title="Overview">
        <FieldGrid rows={overviewRows} />
        {synonymNames.length > 0 && (
          <div className="mt-6">
            <p className="mb-2 font-sans text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
              Synonyms
            </p>
            <ChipList items={synonymNames} />
          </div>
        )}
      </Section>

      <Section title="Distribution">
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-5">
            <div>
              <p className="mb-2 font-sans text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
                Native
              </p>
              <ChipList items={nativeFallback} initialVisible={12} />
            </div>
            <div>
              <p className="mb-2 font-sans text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
                Introduced
              </p>
              <ChipList items={introducedFallback} initialVisible={12} />
            </div>
          </div>
          <DistributionGlobe places={nativeFallback} label="Native range globe" />
        </div>
      </Section>
    </div>
  );
}
