export const COMPARE_STORAGE_KEY = "plantdex.compare.slugs";
export const COMPARE_MIN = 2;
export const COMPARE_MAX = 4;

export type ComparePlantRef = {
  slug: string;
  common_name?: string | null;
  scientific_name?: string | null;
  image_url?: string | null;
};

function readRaw(): ComparePlantRef[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(COMPARE_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item) => item && typeof item.slug === "string" && item.slug.trim())
      .slice(0, COMPARE_MAX);
  } catch {
    return [];
  }
}

function writeRaw(items: ComparePlantRef[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(COMPARE_STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("plantdex:compare-updated"));
}

export function getCompareList(): ComparePlantRef[] {
  return readRaw();
}

export function isInCompare(slug: string): boolean {
  return readRaw().some((item) => item.slug === slug);
}

export function addToCompare(plant: ComparePlantRef): {
  ok: boolean;
  reason?: "duplicate" | "full" | "invalid";
  list: ComparePlantRef[];
} {
  const slug = plant.slug?.trim();
  if (!slug) return { ok: false, reason: "invalid", list: readRaw() };

  const current = readRaw();
  if (current.some((item) => item.slug === slug)) {
    return { ok: false, reason: "duplicate", list: current };
  }
  if (current.length >= COMPARE_MAX) {
    return { ok: false, reason: "full", list: current };
  }

  const next = [
    ...current,
    {
      slug,
      common_name: plant.common_name ?? null,
      scientific_name: plant.scientific_name ?? null,
      image_url: plant.image_url ?? null,
    },
  ];
  writeRaw(next);
  return { ok: true, list: next };
}

export function removeFromCompare(slug: string): ComparePlantRef[] {
  const next = readRaw().filter((item) => item.slug !== slug);
  writeRaw(next);
  return next;
}

export function clearCompare(): void {
  writeRaw([]);
}

export function compareHref(slugs: string[] = getCompareList().map((p) => p.slug)): string {
  const cleaned = slugs.map((s) => s.trim()).filter(Boolean).slice(0, COMPARE_MAX);
  if (!cleaned.length) return "/compare";
  return `/compare?plants=${cleaned.map(encodeURIComponent).join(",")}`;
}

export function parseCompareSlugs(param: string | null | undefined): string[] {
  if (!param) return [];
  return param
    .split(",")
    .map((s) => decodeURIComponent(s.trim()))
    .filter(Boolean)
    .slice(0, COMPARE_MAX);
}
