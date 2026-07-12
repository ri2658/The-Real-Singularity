import type { PlantProfile } from "@/lib/api";

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Unknown";
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "Unknown";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return String(value);
}

export default function PlantProfileHeader({ plant }: { plant: PlantProfile }) {
  const name = plant.common_name || plant.scientific_name || "Unknown plant";

  return (
    <section className="grid gap-8 md:grid-cols-[360px_1fr]">
      <div className="overflow-hidden rounded-3xl border bg-white shadow-sm">
        <div className="aspect-square bg-neutral-100">
          {plant.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={plant.image_url}
              alt={name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-neutral-500">
              No image available
            </div>
          )}
        </div>
      </div>

      <div className="rounded-3xl border bg-white p-8 shadow-sm">
        <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-green-700">
          Plant profile
        </p>

        <h1 className="text-4xl font-bold text-neutral-950">{name}</h1>

        <p className="mt-2 text-xl italic text-neutral-500">
          {plant.scientific_name || "Scientific name unavailable"}
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <Info label="Genus" value={plant.genus} />
          <Info label="Family" value={plant.family} />
          <Info label="Family common name" value={plant.family_common_name} />
          <Info label="Edible" value={formatValue(plant.edible)} />
          <Info label="Edible part" value={formatValue(plant.edible_part)} />
          <Info label="Duration" value={plant.duration} />
        </div>
      </div>
    </section>
  );
}

function Info({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-2xl bg-neutral-50 p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">
        {label}
      </div>
      <div className="mt-1 font-medium text-neutral-900">
        {formatValue(value)}
      </div>
    </div>
  );
}