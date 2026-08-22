import Link from "next/link";
import type { PlantCard as PlantCardType } from "@/lib/api";

export default function PlantCard({ plant }: { plant: PlantCardType }) {
  const name = plant.common_name || plant.scientific_name || "Unknown plant";
  const scientificName = plant.scientific_name || "Scientific name unavailable";
  const slug = plant.slug;

  const card = (
    <div className="group overflow-hidden rounded-sm border border-border-plant bg-parchment transition-all duration-300 hover:border-fern hover:shadow-md">
      {/* Image area */}
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-mist">
        {plant.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={plant.image_url}
            alt={name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <span className="font-display text-xs italic text-ink-muted opacity-40">
              No specimen image
            </span>
          </div>
        )}

        {/* Taxonomy slide-up — reveals on hover */}
        {(plant.genus || plant.family) && (
          <div className="absolute bottom-0 left-0 right-0 translate-y-full bg-gradient-to-t from-forest/85 to-transparent p-3 transition-transform duration-300 ease-out group-hover:translate-y-0">
            <div className="flex flex-wrap gap-1.5">
              {plant.genus && (
                <span className="rounded-full border border-white/20 bg-canopy/75 px-2.5 py-0.5 text-xs text-white backdrop-blur-sm">
                  {plant.genus}
                </span>
              )}
              {plant.family && (
                <span className="rounded-full border border-white/20 bg-canopy/75 px-2.5 py-0.5 text-xs text-white/75 backdrop-blur-sm">
                  {plant.family}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Card body */}
      <div className="p-4">
        <h3 className="font-display line-clamp-1 text-base font-semibold leading-snug text-ink">
          {name}
        </h3>
        <p className="font-display mt-0.5 line-clamp-1 text-sm font-light italic text-ink-muted">
          {scientificName}
        </p>
      </div>
    </div>
  );

  if (!slug) return card;

  return (
    <Link href={`/plants/${slug}`} className="block">
      {card}
    </Link>
  );
}
