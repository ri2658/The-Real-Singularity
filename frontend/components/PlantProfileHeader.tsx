import type { PlantProfile } from "@/lib/api";

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Unknown";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "Unknown";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export default function PlantProfileHeader({ plant }: { plant: PlantProfile }) {
  const name = plant.common_name || plant.scientific_name || "Unknown plant";

  return (
    <section className="grid gap-6 md:grid-cols-[380px_1fr]">
      {/* Specimen image */}
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

      {/* Plant info */}
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

          <div className="my-7 h-px bg-border-plant" />

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Info label="Genus" value={plant.genus} />
            <Info label="Family" value={plant.family} />
            <Info label="Family name" value={plant.family_common_name} />
            <Info label="Edible" value={formatValue(plant.edible)} />
            <Info label="Edible part" value={formatValue(plant.edible_part)} />
            <Info label="Duration" value={plant.duration} />
          </div>
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
