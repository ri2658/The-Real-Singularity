import Link from "next/link";
import type { PlantCard as PlantCardType } from "@/lib/api";

export default function PlantCard({ plant }: { plant: PlantCardType }) {
  const name = plant.common_name || plant.scientific_name || "Unknown plant";
  const scientificName = plant.scientific_name || "Scientific name unavailable";
  const slug = plant.slug;

  const card = (
    <div className="group overflow-hidden rounded-2xl border bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-md">
      <div className="aspect-[4/3] w-full bg-neutral-100">
        {plant.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={plant.image_url}
            alt={name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-sm text-neutral-500">
            No image available
          </div>
        )}
      </div>

      <div className="space-y-2 p-4">
        <div>
          <h3 className="line-clamp-1 font-semibold text-neutral-900">
            {name}
          </h3>
          <p className="line-clamp-1 text-sm italic text-neutral-500">
            {scientificName}
          </p>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          {plant.genus && (
            <span className="rounded-full bg-green-50 px-2 py-1 text-green-700">
              {plant.genus}
            </span>
          )}
          {plant.family && (
            <span className="rounded-full bg-blue-50 px-2 py-1 text-blue-700">
              {plant.family}
            </span>
          )}
        </div>
      </div>
    </div>
  );

  if (!slug) {
    return card;
  }

  return (
    <Link href={`/plants/${slug}`} className="block">
      {card}
    </Link>
  );
}