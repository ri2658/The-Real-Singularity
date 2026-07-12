import Link from "next/link";
import PlantProfileHeader from "@/components/PlantProfileHeader";
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
    <main className="min-h-screen bg-neutral-50">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <Link href="/" className="text-sm font-medium text-green-700 hover:text-green-900">
          ← Back to search
        </Link>

        <div className="mt-8">
          <PlantProfileHeader plant={plant} />
        </div>

        <div className="mt-10">
          <div className="mb-5">
            <p className="text-sm font-semibold uppercase tracking-wide text-green-700">
              Related discovery
            </p>
            <h2 className="text-3xl font-bold text-neutral-950">
              Explore connected plants
            </h2>
            <p className="mt-2 text-neutral-600">
              PlantDex compares taxonomy, distribution, and selected traits to
              surface related or similar plants.
            </p>
          </div>

          <div className="space-y-6">
            <RelatedPlantsSection query={query} basis="genus" />
            <RelatedPlantsSection query={query} basis="family" />
            <RelatedPlantsSection query={query} basis="distribution" />
            <RelatedPlantsSection query={query} basis="edible_part" />
            <RelatedPlantsSection query={query} basis="growth_habit" />
            <RelatedPlantsSection query={query} basis="fruit_color" />
          </div>
        </div>
      </div>
    </main>
  );
}