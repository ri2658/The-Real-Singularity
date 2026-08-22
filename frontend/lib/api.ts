const API_BASE_URL = process.env.NEXT_PUBLIC_PLANTDEX_API_URL;

if (!API_BASE_URL) {
  throw new Error("Missing NEXT_PUBLIC_PLANTDEX_API_URL");
}

export type PlantCard = {
  id?: number | string | null;
  slug?: string | null;
  common_name?: string | null;
  scientific_name?: string | null;
  family?: string | null;
  family_common_name?: string | null;
  genus?: string | null;
  genus_id?: number | string | null;
  image_url?: string | null;
  rank?: string | null;
  status?: string | null;
  vegetable?: boolean | null;
  edible?: boolean | null;
  links?: Record<string, unknown>;
};

export type SearchResponse = {
  query: string;
  max_results: number;
  image_only: boolean;
  count: number;
  results: PlantCard[];
  warnings: string[];
  cache?: {
    hit: boolean;
    cache_key: string;
  };
};

export type PlantProfile = {
  id?: number | string | null;
  slug?: string | null;
  common_name?: string | null;
  scientific_name?: string | null;
  image_url?: string | null;
  family?: string | null;
  family_slug?: string | null;
  family_common_name?: string | null;
  genus?: string | null;
  genus_slug?: string | null;
  vegetable?: boolean | null;
  edible?: boolean | null;
  edible_part?: string[] | string | null;
  distribution?: Record<string, unknown> | null;
  distributions?: Record<string, unknown> | null;
  duration?: string | null;
  flower?: Record<string, unknown> | null;
  foliage?: Record<string, unknown> | null;
  fruit_or_seed?: Record<string, unknown> | null;
  specifications?: Record<string, unknown> | null;
  growth?: Record<string, unknown> | null;
  links?: Record<string, unknown>;
  /** Full Trefle plant payload for richer profile rendering */
  raw?: Record<string, unknown> | null;
};

export type PlantProfileResponse = {
  slug: string;
  plant: PlantProfile;
  warnings: string[];
  cache?: {
    hit: boolean;
    cache_key: string;
  };
};

export type SimilarResponse = {
  basis: string;
  query?: string;
  count: number;
  results: PlantCard[];
  warnings: string[];
  request?: {
    query: string;
    basis: string;
    max_results: number;
    image_only: boolean;
  };
  timing?: {
    duration_seconds: number;
  };
  cache?: {
    hit: boolean;
    cache_key: string;
  };
};

export async function searchPlants({
  query,
  maxResults = 12,
  imageOnly = false,
}: {
  query: string;
  maxResults?: number;
  imageOnly?: boolean;
}): Promise<SearchResponse> {
  const params = new URLSearchParams({
    query,
    max_results: String(maxResults),
    image_only: String(imageOnly),
  });

  const res = await fetch(`${API_BASE_URL}/search?${params.toString()}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Search failed with status ${res.status}`);
  }

  return res.json();
}

export async function getPlantProfile(
  slug: string
): Promise<PlantProfileResponse> {
  const res = await fetch(`${API_BASE_URL}/plants/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Plant profile failed with status ${res.status}`);
  }

  return res.json();
}

export type TrefleFeedbackResponse = {
  ok: boolean;
  type: "report" | "correction";
  species_id: string;
  trefle?: Record<string, unknown>;
  error?: string;
  message?: string;
};

export async function reportPlantError({
  slug,
  speciesId,
  notes,
}: {
  slug: string;
  speciesId?: string | null;
  notes: string;
}): Promise<TrefleFeedbackResponse> {
  const res = await fetch(
    `${API_BASE_URL}/plants/${encodeURIComponent(slug)}/report`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        notes,
        species_id: speciesId || undefined,
      }),
    }
  );

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      data.message || data.error || `Report failed with status ${res.status}`
    );
  }
  return data;
}

export async function submitPlantCorrection({
  slug,
  speciesId,
  notes,
  sourceType,
  sourceReference,
  correction,
}: {
  slug: string;
  speciesId?: string | null;
  notes?: string;
  sourceType: "external" | "user_observation" | "publication";
  sourceReference: string;
  correction: Record<string, string | number | boolean>;
}): Promise<TrefleFeedbackResponse> {
  const res = await fetch(
    `${API_BASE_URL}/plants/${encodeURIComponent(slug)}/corrections`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        notes: notes || undefined,
        source_type: sourceType,
        source_reference: sourceReference,
        correction,
        species_id: speciesId || undefined,
      }),
    }
  );

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      data.message || data.error || `Correction failed with status ${res.status}`
    );
  }
  return data;
}

export async function getSimilarPlants({
  query,
  basis,
  maxResults = 6,
  imageOnly = false,
}: {
  query: string;
  basis: string;
  maxResults?: number;
  imageOnly?: boolean;
}): Promise<SimilarResponse> {
  const params = new URLSearchParams({
    query,
    basis,
    max_results: String(maxResults),
    image_only: String(imageOnly),
  });

  return withSimilarConcurrency(async () => {
    const url = `${API_BASE_URL}/similar?${params.toString()}`;
    // Profile pages fire many /similar calls at once; 503 is usually API Gateway
    // timing out an overloaded Lambda. Retry once after a short backoff.
    const attempts = 2;
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= attempts; attempt++) {
      const res = await fetch(url, { cache: "no-store" });

      if (res.ok) {
        return res.json();
      }

      const retryable = res.status === 502 || res.status === 503 || res.status === 504;
      lastError = new Error(`Similar plants failed with status ${res.status}`);

      if (!retryable || attempt === attempts) {
        throw lastError;
      }

      await sleep(400 * attempt);
    }

    throw lastError || new Error("Similar plants failed");
  });
}

let similarInFlight = 0;
const SIMILAR_MAX_CONCURRENT = 2;
const similarWaiters: Array<() => void> = [];

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function withSimilarConcurrency<T>(fn: () => Promise<T>): Promise<T> {
  if (similarInFlight >= SIMILAR_MAX_CONCURRENT) {
    await new Promise<void>((resolve) => similarWaiters.push(resolve));
  }

  similarInFlight += 1;
  try {
    return await fn();
  } finally {
    similarInFlight -= 1;
    const next = similarWaiters.shift();
    if (next) next();
  }
}