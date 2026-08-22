import Link from "next/link";
import PlantProfileHeader from "@/components/PlantProfileHeader";
import PlantAiSummary from "@/components/PlantAiSummary";
import PlantProfileDetails from "@/components/PlantProfileDetails";
import PlantDataFeedback from "@/components/PlantDataFeedback";
import RelatedPlantsSection from "@/components/RelatedPlantsSection";
import { getPlantProfile } from "@/lib/api";

export default async function PlantPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const data = await getPlantProfile(slug);
  const plant = data.plant;
  const query = plant.slug || slug;

  return (
    <main className="min-h-screen bg-mist">
      {/* Nav strip */}
      <div className="border-b border-border-plant bg-parchment">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <Link
            href="/"
            className="font-sans text-sm font-medium text-fern transition-colors hover:text-canopy"
          >
            ← PlantDex
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 py-10 pb-8">
        <PlantProfileHeader plant={plant} />
        <PlantAiSummary plant={plant} />
        <PlantProfileDetails plant={plant} />

        <div className="mt-14">
          <div className="mb-7">
            <p className="mb-2 font-sans text-xs font-semibold uppercase tracking-[0.18em] text-fern">
              Related discovery
            </p>
            <h2 className="font-display text-4xl font-light text-ink">
              Explore connected plants
            </h2>
            <p className="mt-2 font-sans text-sm text-ink-muted">
              PlantDex traces taxonomy, geography, and traits to surface species
              related to{" "}
              <em className="font-display italic">
                {plant.common_name || plant.scientific_name || "this plant"}
              </em>
              .
            </p>
          </div>

          <div className="space-y-5">
            <RelatedPlantsSection query={query} basis="genus" />
            <RelatedPlantsSection query={query} basis="family" />
            <RelatedPlantsSection query={query} basis="distribution" />
            <RelatedPlantsSection query={query} basis="edible_part" />
            <RelatedPlantsSection query={query} basis="growth_habit" />
            <RelatedPlantsSection query={query} basis="fruit_color" />
          </div>
        </div>

        <PlantDataFeedback plant={plant} />
      </div>
    </main>
  );
}
