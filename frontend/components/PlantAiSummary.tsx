"use client";

import AiSummaryCard from "@/components/AiSummaryCard";
import { fetchPlantSummary } from "@/lib/ai";
import type { PlantProfile } from "@/lib/api";

export default function PlantAiSummary({ plant }: { plant: PlantProfile }) {
  const scientific = plant.scientific_name?.trim() || null;
  const common = plant.common_name?.trim() || null;
  const label = scientific || common || "this plant";

  return (
    <div className="mt-10">
      <AiSummaryCard
        title="AI plant overview"
        subtitle={
          scientific
            ? `Looked up as ${scientific}${common ? ` (${common})` : ""}`
            : `Context and caveats for ${label}`
        }
        loadKey={`plant:${plant.slug || scientific || label}`}
        loader={() =>
          fetchPlantSummary({
            plant: {
              common_name: plant.common_name,
              scientific_name: plant.scientific_name,
              family: plant.family,
              family_common_name: plant.family_common_name,
              genus: plant.genus,
              edible: plant.edible,
              edible_part: plant.edible_part,
              vegetable: plant.vegetable,
              duration: plant.duration,
              distribution: plant.distribution,
              flower: plant.flower,
              foliage: plant.foliage,
              fruit_or_seed: plant.fruit_or_seed,
              specifications: plant.specifications,
              growth: plant.growth,
            },
          })
        }
      />
    </div>
  );
}
