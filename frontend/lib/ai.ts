export type AiSummaryPayload = {
  summary: string;
  /** Kept for API compatibility; UI no longer renders these. */
  highlights?: string[];
  sources?: unknown[];
  tasting_video?: unknown;
  model?: string;
};

export type SearchSummaryRequest = {
  query: string;
  results: Array<{
    common_name?: string | null;
    scientific_name?: string | null;
    family?: string | null;
    genus?: string | null;
    edible?: boolean | null;
    vegetable?: boolean | null;
    status?: string | null;
  }>;
};

export type PlantSummaryRequest = {
  plant: {
    common_name?: string | null;
    scientific_name?: string | null;
    family?: string | null;
    family_common_name?: string | null;
    genus?: string | null;
    edible?: boolean | null;
    edible_part?: string[] | string | null;
    vegetable?: boolean | null;
    duration?: string | null;
    distribution?: Record<string, unknown> | null;
    flower?: Record<string, unknown> | null;
    foliage?: Record<string, unknown> | null;
    fruit_or_seed?: Record<string, unknown> | null;
    specifications?: Record<string, unknown> | null;
    growth?: Record<string, unknown> | null;
  };
};

export async function fetchSearchSummary(
  body: SearchSummaryRequest
): Promise<AiSummaryPayload> {
  const res = await fetch("/api/ai/search-summary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `AI summary failed (${res.status})`);
  }
  return data as AiSummaryPayload;
}

export async function fetchPlantSummary(
  body: PlantSummaryRequest
): Promise<AiSummaryPayload> {
  const res = await fetch("/api/ai/plant-summary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `AI summary failed (${res.status})`);
  }
  return data as AiSummaryPayload;
}
