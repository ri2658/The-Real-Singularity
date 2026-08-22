import { NextResponse } from "next/server";
import { summarizeSearchResults } from "@/lib/openai-server";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const query = typeof body?.query === "string" ? body.query.trim() : "";
    const results = Array.isArray(body?.results) ? body.results : [];

    if (!query) {
      return NextResponse.json({ error: "query is required" }, { status: 400 });
    }
    if (!results.length) {
      return NextResponse.json(
        { error: "results are required" },
        { status: 400 }
      );
    }

    const slim = results.slice(0, 16).map((r: Record<string, unknown>) => ({
      common_name: r.common_name ?? null,
      scientific_name: r.scientific_name ?? null,
      family: r.family ?? null,
      genus: r.genus ?? null,
      edible: r.edible ?? null,
      vegetable: r.vegetable ?? null,
      status: r.status ?? null,
      rank: r.rank ?? null,
    }));

    const summary = await summarizeSearchResults({ query, results: slim });
    return NextResponse.json(summary);
  } catch (err) {
    const message = err instanceof Error ? err.message : "AI summary failed";
    const status = message.includes("OPENAI_API_KEY") ? 503 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
