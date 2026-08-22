import { NextResponse } from "next/server";
import { summarizePlantProfile } from "@/lib/openai-server";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const plant = body?.plant;

    if (!plant || typeof plant !== "object") {
      return NextResponse.json({ error: "plant is required" }, { status: 400 });
    }

    const p = plant as Record<string, unknown>;
    const slim = {
      common_name: p.common_name ?? null,
      scientific_name: p.scientific_name ?? null,
      family: p.family ?? null,
      family_common_name: p.family_common_name ?? null,
      genus: p.genus ?? null,
      edible: p.edible ?? null,
      edible_part: p.edible_part ?? null,
      vegetable: p.vegetable ?? null,
      duration: p.duration ?? null,
      distribution: p.distribution ?? null,
      flower: p.flower ?? null,
      foliage: p.foliage ?? null,
      fruit_or_seed: p.fruit_or_seed ?? null,
      specifications: p.specifications ?? null,
      growth: p.growth ?? null,
    };

    const summary = await summarizePlantProfile({ plant: slim });
    return NextResponse.json(summary);
  } catch (err) {
    const message = err instanceof Error ? err.message : "AI summary failed";
    const status = message.includes("OPENAI_API_KEY") ? 503 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
