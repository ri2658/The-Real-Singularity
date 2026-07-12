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

  const res = await fetch(`${API_BASE_URL}/similar?${params.toString()}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Similar plants failed with status ${res.status}`);
  }

  return res.json();
}