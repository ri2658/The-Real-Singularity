/** Resolve Trefle distribution place names to lat/lng via Photon (OSM). */

export const NATIVE_COLOR = "#6BB87A";
export const INTRODUCED_COLOR = "#E8A54B";

export type GeoPoint = {
  name: string;
  lat: number;
  lng: number;
};

const PHOTON_URL = "https://photon.komoot.io/api/";
const CACHE_KEY = "plantdex.geocode.v1";
const CACHE_TTL_MS = 1000 * 60 * 60 * 24 * 30; // 30 days

/** Tiny alias map for Trefle typos / abbreviations only — not a place gazetteer */
const ALIASES: Record<string, string> = {
  masachusettes: "Massachusetts",
  "rhode i": "Rhode Island",
  "rhode i.": "Rhode Island",
  "canary is": "Canary Islands",
  "canary is.": "Canary Islands",
  "balearic is": "Balearic Islands",
  "balearic is.": "Balearic Islands",
  "windward is": "Windward Islands",
  "windward is.": "Windward Islands",
  "leeward is": "Leeward Islands",
  "leeward is.": "Leeward Islands",
  czechoslovakia: "Czech Republic",
  "northern prov": "Northern Provinces South Africa",
  "cape provinces": "Cape Province South Africa",
  "china north-central": "North Central China",
  "china south-central": "South Central China",
  "china southeast": "Southeast China",
  "mexico central": "Central Mexico",
  "mexico gulf": "Gulf of Mexico Mexico",
  "mexico northeast": "Northeast Mexico",
  "mexico northwest": "Northwest Mexico",
  "mexico southeast": "Southeast Mexico",
  "mexico southwest": "Southwest Mexico",
  "east himalaya": "Eastern Himalayas",
  "west himalaya": "Western Himalayas",
  "central european russia": "Central European Russia",
  "east european russia": "Eastern European Russia",
  "north european russia": "Northern European Russia",
  "northwest european russia": "Northwest European Russia",
  "south european russia": "Southern European Russia",
  "west siberia": "Western Siberia",
  "east siberia": "Eastern Siberia",
  jawa: "Java Indonesia",
  sumatera: "Sumatra Indonesia",
  malaya: "Peninsular Malaysia",
  "lesser sundas": "Lesser Sunda Islands",
  "new guinea": "New Guinea",
  "korea peninsula": "Korean Peninsula",
  yakutskiya: "Yakutia Russia",
  buryatiya: "Buryatia Russia",
  primorye: "Primorsky Krai Russia",
};

type CacheEntry = {
  lat: number | null;
  lng: number | null;
  at: number;
};

type CacheStore = Record<string, CacheEntry>;

function normalizeKey(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\./g, "")
    .replace(/'/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function queryFor(name: string): string {
  const key = normalizeKey(name);
  return ALIASES[key] || ALIASES[name.toLowerCase().trim()] || name;
}

function readCache(): CacheStore {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(CACHE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as CacheStore;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeCache(store: CacheStore) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(CACHE_KEY, JSON.stringify(store));
  } catch {
    // ignore quota errors
  }
}

function getCached(name: string): GeoPoint | null | undefined {
  const store = readCache();
  const entry = store[normalizeKey(name)];
  if (!entry) return undefined;
  if (Date.now() - entry.at > CACHE_TTL_MS) return undefined;
  if (entry.lat === null || entry.lng === null) return null;
  return { name, lat: entry.lat, lng: entry.lng };
}

function setCached(name: string, point: GeoPoint | null) {
  const store = readCache();
  store[normalizeKey(name)] = {
    lat: point?.lat ?? null,
    lng: point?.lng ?? null,
    at: Date.now(),
  };
  writeCache(store);
}

async function geocodeOne(name: string): Promise<GeoPoint | null> {
  const cached = getCached(name);
  if (cached !== undefined) return cached;

  const q = queryFor(name);
  const url = `${PHOTON_URL}?q=${encodeURIComponent(q)}&limit=1`;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      setCached(name, null);
      return null;
    }

    const data = (await res.json()) as {
      features?: Array<{ geometry?: { coordinates?: number[] } }>;
    };
    const coords = data.features?.[0]?.geometry?.coordinates;
    if (!coords || coords.length < 2) {
      setCached(name, null);
      return null;
    }

    const [lng, lat] = coords;
    if (typeof lat !== "number" || typeof lng !== "number") {
      setCached(name, null);
      return null;
    }

    const point = { name, lat, lng };
    setCached(name, point);
    return point;
  } catch {
    // Don't cache network blips as permanent misses
    return null;
  }
}

/** Resolve many place names with light concurrency + local cache. */
export async function resolvePlaces(names: string[]): Promise<{
  points: GeoPoint[];
  unresolved: string[];
}> {
  const unique = Array.from(new Set(names.map((n) => n.trim()).filter(Boolean)));
  const points: GeoPoint[] = [];
  const unresolved: string[] = [];

  // Small concurrency to stay polite to the free Photon API
  const concurrency = 4;
  let i = 0;

  async function worker() {
    while (i < unique.length) {
      const name = unique[i++];
      const point = await geocodeOne(name);
      if (point) points.push(point);
      else unresolved.push(name);
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, unique.length) }, () => worker())
  );

  return { points, unresolved };
}

export function extractDistributionNames(
  distribution: Record<string, unknown> | null | undefined,
  key: "native" | "introduced" = "native"
): string[] {
  if (!distribution || typeof distribution !== "object") return [];
  const value = distribution[key];
  if (!Array.isArray(value)) return [];

  return value
    .map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "name" in item) {
        return String((item as { name: unknown }).name);
      }
      return "";
    })
    .filter(Boolean);
}
