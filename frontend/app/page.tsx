"use client";

import { useState, useEffect } from "react";
import SearchBar from "@/components/SearchBar";
import PlantCard from "@/components/PlantCard";
import { searchPlants, type PlantCard as PlantCardType } from "@/lib/api";

function SkeletonCard() {
  return (
    <div className="overflow-hidden rounded-sm border border-border-plant bg-parchment">
      <div className="aspect-[4/3] w-full shimmer" />
      <div className="space-y-2 p-4">
        <div className="h-5 w-3/4 rounded shimmer" />
        <div className="h-4 w-1/2 rounded shimmer" />
        <div className="mt-1 flex gap-2">
          <div className="h-3.5 w-16 rounded-full shimmer" />
          <div className="h-3.5 w-20 rounded-full shimmer" />
        </div>
      </div>
    </div>
  );
}

/* ── Background decoration ─────────────────────────────────── */

function LeafSVG({ color = "#3D6B4A" }: { color?: string }) {
  return (
    <>
      <path
        d="M30 2 C52 8 58 46 30 98 C8 46 8 8 30 2 Z"
        stroke={color}
        strokeWidth="1.2"
        fill="none"
      />
      <line x1="30" y1="5" x2="30" y2="93" stroke={color} strokeWidth="0.8" />
      <line x1="30" y1="22" x2="47" y2="38" stroke={color} strokeWidth="0.6" />
      <line x1="30" y1="40" x2="50" y2="55" stroke={color} strokeWidth="0.6" />
      <line x1="30" y1="58" x2="47" y2="70" stroke={color} strokeWidth="0.6" />
      <line x1="30" y1="22" x2="13" y2="38" stroke={color} strokeWidth="0.6" />
      <line x1="30" y1="40" x2="10" y2="55" stroke={color} strokeWidth="0.6" />
      <line x1="30" y1="58" x2="13" y2="70" stroke={color} strokeWidth="0.6" />
    </>
  );
}

function FanLeafSVG({ color = "#3D6B4A" }: { color?: string }) {
  return (
    <>
      <path d="M40 65 C35 55 12 38 5 12" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <path d="M40 65 C38 52 26 28 22 4" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <path d="M40 65 L40 4" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <path d="M40 65 C42 52 54 28 58 4" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <path d="M40 65 C45 55 68 38 75 12" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <ellipse cx="6" cy="12" rx="6" ry="11" stroke={color} strokeWidth="1" fill="none" transform="rotate(-22 6 12)" />
      <ellipse cx="23" cy="5" rx="6" ry="10" stroke={color} strokeWidth="1" fill="none" transform="rotate(-5 23 5)" />
      <ellipse cx="40" cy="5" rx="6" ry="10" stroke={color} strokeWidth="1" fill="none" />
      <ellipse cx="57" cy="5" rx="6" ry="10" stroke={color} strokeWidth="1" fill="none" transform="rotate(5 57 5)" />
      <ellipse cx="74" cy="12" rx="6" ry="11" stroke={color} strokeWidth="1" fill="none" transform="rotate(22 74 12)" />
    </>
  );
}

function CherryPair() {
  return (
    <>
      <path d="M20 22 Q15 12 11 5" stroke="#7A3B1E" strokeWidth="2" strokeLinecap="round" fill="none" />
      <path d="M20 22 Q25 12 29 5" stroke="#7A3B1E" strokeWidth="2" strokeLinecap="round" fill="none" />
      <circle cx="11" cy="34" r="12" fill="#EF4444" />
      <circle cx="29" cy="36" r="12" fill="#DC2626" />
      <circle cx="8" cy="30.5" r="3.5" fill="rgba(255,255,255,0.42)" />
      <circle cx="26" cy="32.5" r="3" fill="rgba(255,255,255,0.38)" />
    </>
  );
}

function OrangeSlice() {
  return (
    <>
      <circle cx="20" cy="20" r="19" fill="#F97316" opacity="0.92" />
      <circle cx="20" cy="20" r="14" fill="#FED7AA" opacity="0.65" />
      <circle cx="20" cy="20" r="3.5" fill="#EA6A00" />
      <line x1="20" y1="6" x2="20" y2="34" stroke="#EA6A00" strokeWidth="1" />
      <line x1="6" y1="20" x2="34" y2="20" stroke="#EA6A00" strokeWidth="1" />
      <line x1="10" y1="10" x2="30" y2="30" stroke="#EA6A00" strokeWidth="1" />
      <line x1="30" y1="10" x2="10" y2="30" stroke="#EA6A00" strokeWidth="1" />
    </>
  );
}

function BlueberryCluster() {
  return (
    <>
      <circle cx="15" cy="25" r="13" fill="#7C3AED" />
      <circle cx="35" cy="23" r="13" fill="#6D28D9" />
      <circle cx="25" cy="35" r="12" fill="#5B21B6" />
      {/* Specular */}
      <circle cx="12" cy="21" r="3.5" fill="rgba(255,255,255,0.32)" />
      <circle cx="32" cy="19" r="3" fill="rgba(255,255,255,0.28)" />
      {/* Crown marks */}
      <g fill="none" stroke="#4C1D95" strokeWidth="0.9" strokeLinecap="round">
        <path d="M15 13 L15 10 M12.5 14 L10.5 11.5 M17.5 14 L19.5 11.5 M11.5 16 L9 15 M18.5 16 L21 15" />
        <path d="M35 11 L35 8 M32.5 12 L30.5 9.5 M37.5 12 L39.5 9.5 M31.5 14 L29 13 M38.5 14 L41 13" />
      </g>
    </>
  );
}

function StrawberryPair() {
  return (
    <>
      {/* First strawberry */}
      <path d="M14 10 C4 10, 1 20, 3 28 C5 35, 10 42, 14 44 C18 42, 23 35, 25 28 C27 20, 24 10, 14 10 Z" fill="#EF4444" />
      <path d="M10 8 C8 3 14 4 14 8 M14 8 C14 4 20 3 18 8 M6 9 C5 5 10 7 10 10" fill="#15803D" stroke="none" />
      <circle cx="11" cy="20" r="1.2" fill="rgba(255,255,230,0.55)" />
      <circle cx="17" cy="18" r="1.2" fill="rgba(255,255,230,0.55)" />
      <circle cx="10" cy="28" r="1.2" fill="rgba(255,255,230,0.55)" />
      <circle cx="18" cy="28" r="1.2" fill="rgba(255,255,230,0.55)" />
      <circle cx="14" cy="35" r="1.2" fill="rgba(255,255,230,0.55)" />
      <circle cx="9" cy="16" r="2.8" fill="rgba(255,255,255,0.32)" />
      {/* Second strawberry offset */}
      <path d="M36 16 C26 16, 23 26, 25 34 C27 41, 32 48, 36 50 C40 48, 45 41, 47 34 C49 26, 46 16, 36 16 Z" fill="#DC2626" />
      <path d="M32 14 C30 9 36 10 36 14 M36 14 C36 10 42 9 40 14 M28 15 C27 11 32 13 32 16" fill="#166534" stroke="none" />
      <circle cx="33" cy="26" r="1.2" fill="rgba(255,255,230,0.5)" />
      <circle cx="39" cy="24" r="1.2" fill="rgba(255,255,230,0.5)" />
      <circle cx="32" cy="34" r="1.2" fill="rgba(255,255,230,0.5)" />
      <circle cx="40" cy="34" r="1.2" fill="rgba(255,255,230,0.5)" />
      <circle cx="36" cy="41" r="1.2" fill="rgba(255,255,230,0.5)" />
      <circle cx="31" cy="22" r="2.5" fill="rgba(255,255,255,0.28)" />
    </>
  );
}

function GrapeCluster() {
  return (
    <>
      {/* Top row */}
      <circle cx="20" cy="12" r="10" fill="#9333EA" />
      {/* Second row */}
      <circle cx="11" cy="26" r="10" fill="#7E22CE" />
      <circle cx="29" cy="26" r="10" fill="#9333EA" />
      {/* Third row */}
      <circle cx="20" cy="40" r="10" fill="#6B21A8" />
      {/* Bottom */}
      <circle cx="20" cy="52" r="8" fill="#7E22CE" />
      {/* Stem */}
      <path d="M20 3 C20 0 22 -2 24 -3" stroke="#713F12" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      {/* Speculars */}
      <circle cx="17" cy="9" r="2.5" fill="rgba(255,255,255,0.3)" />
      <circle cx="8" cy="23" r="2" fill="rgba(255,255,255,0.25)" />
      <circle cx="26" cy="23" r="2" fill="rgba(255,255,255,0.25)" />
    </>
  );
}

function HeroBackground({ mx, my }: { mx: number; my: number }) {
  const layer = (factor: number, delay: string) => ({
    transform: `translate(${mx * factor}px, ${my * factor}px)`,
    transition: `transform ${delay} ease-out`,
    position: "absolute" as const,
    inset: 0,
  });

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden select-none">

      {/* ── Layer 1: Far — large leaf imprints ─────────────────── */}
      <div style={layer(15, "0.9s")}>
        {/* Large oval leaf, upper-left */}
        <svg
          viewBox="0 0 60 100"
          className="absolute -left-8 top-[3%] h-72 w-44 opacity-[0.09]"
          style={{ animation: "leaf-drift 22s ease-in-out infinite" }}
        >
          <LeafSVG color="#5A9C6A" />
        </svg>

        {/* Fan leaf, lower-right */}
        <svg
          viewBox="0 0 80 70"
          className="absolute -right-6 bottom-[-5%] h-52 w-64 opacity-[0.08] rotate-[160deg]"
          style={{ animation: "leaf-drift-b 26s ease-in-out -7s infinite" }}
        >
          <FanLeafSVG color="#5A9C6A" />
        </svg>
      </div>

      {/* ── Layer 2: Mid — medium leaf shapes ──────────────────── */}
      <div style={layer(28, "0.65s")}>
        {/* Oval leaf, upper-right */}
        <svg
          viewBox="0 0 60 100"
          className="absolute -right-2 top-[18%] h-44 w-28 opacity-[0.11] rotate-[22deg]"
          style={{ animation: "leaf-drift 18s ease-in-out -4s infinite" }}
        >
          <LeafSVG color="#4A8A5A" />
        </svg>

        {/* Small fan leaf, lower-left */}
        <svg
          viewBox="0 0 80 70"
          className="absolute left-[8%] bottom-[5%] h-32 w-44 opacity-[0.1] -rotate-[12deg]"
          style={{ animation: "leaf-drift-b 20s ease-in-out -11s infinite" }}
        >
          <FanLeafSVG color="#4A8A5A" />
        </svg>

        {/* Thin oval leaf, center-right */}
        <svg
          viewBox="0 0 60 100"
          className="absolute right-[22%] top-[8%] h-28 w-16 opacity-[0.09] -rotate-[8deg]"
          style={{ animation: "leaf-drift 14s ease-in-out -9s infinite" }}
        >
          <LeafSVG color="#3D7A4F" />
        </svg>
      </div>

      {/* ── Layer 3: Foreground — colorful fruits ──────────────── */}
      <div style={layer(46, "0.4s")}>
        {/* Cherry pair — upper-left zone */}
        <svg
          viewBox="0 0 40 50"
          className="absolute top-[14%] left-[6%] h-20 w-16 opacity-[0.78]"
          style={{ animation: "bob 4.2s ease-in-out infinite" }}
        >
          <CherryPair />
        </svg>

        {/* Blueberry cluster — upper-right zone */}
        <svg
          viewBox="0 0 50 48"
          className="absolute top-[10%] right-[9%] h-20 w-20 opacity-[0.72]"
          style={{ animation: "bob 3.6s ease-in-out 0.9s infinite" }}
        >
          <BlueberryCluster />
        </svg>

        {/* Orange slice — lower-left zone */}
        <svg
          viewBox="0 0 40 40"
          className="absolute bottom-[20%] left-[14%] h-16 w-16 opacity-[0.68]"
          style={{ animation: "bob 5.1s ease-in-out 1.7s infinite" }}
        >
          <OrangeSlice />
        </svg>

        {/* Strawberry pair — right edge, mid */}
        <svg
          viewBox="0 0 50 54"
          className="absolute top-[42%] right-[5%] h-20 w-20 opacity-[0.68]"
          style={{ animation: "bob 4.7s ease-in-out 2.4s infinite" }}
        >
          <StrawberryPair />
        </svg>

        {/* Grape cluster — lower-right zone */}
        <svg
          viewBox="0 0 40 60"
          className="absolute bottom-[12%] right-[18%] h-20 w-14 opacity-[0.62]"
          style={{ animation: "bob 3.9s ease-in-out 0.4s infinite" }}
        >
          <GrapeCluster />
        </svg>
      </div>
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────── */

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [plants, setPlants] = useState<PlantCardType[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [cacheHit, setCacheHit] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [mouse, setMouse] = useState({ x: 0, y: 0 });

  useEffect(() => {
    function onMove(e: MouseEvent) {
      setMouse({
        x: (e.clientX - window.innerWidth / 2) / window.innerWidth,
        y: (e.clientY - window.innerHeight / 2) / window.innerHeight,
      });
    }
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  async function handleSearch(nextQuery: string) {
    setQuery(nextQuery);
    setLoading(true);
    setError("");
    setWarnings([]);
    setCacheHit(null);
    setSearched(true);

    try {
      const data = await searchPlants({
        query: nextQuery,
        maxResults: 12,
        imageOnly: false,
      });

      setPlants(data.results || []);
      setWarnings(data.warnings || []);
      setCacheHit(data.cache?.hit ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setPlants([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen">
      {/* ── Hero ────────────────────────────────────────────── */}
      <section className="relative flex min-h-[56vh] flex-col items-center justify-center overflow-hidden bg-forest px-6 py-16 text-center">
        <HeroBackground mx={mouse.x} my={mouse.y} />

        <div className="relative z-10 flex max-w-3xl flex-col items-center">
          <p className="mb-5 font-sans text-xs font-semibold uppercase tracking-[0.22em] text-sprout">
            PlantDex
          </p>

          <h1 className="font-display mb-5 text-5xl font-light leading-tight tracking-tight text-white md:text-7xl">
            Every plant
            <br />
            <em className="italic text-leaf">has a story.</em>
          </h1>

          <p className="mb-8 max-w-md font-sans text-base leading-relaxed text-white/55">
            Search a familiar plant and trace its connections through genus,
            family, distribution, and traits.
          </p>

          <SearchBar onSearch={handleSearch} />

          <div className="mt-5 flex items-center gap-0.5 text-sm text-white/40">
            <span className="mr-1.5">Try</span>
            {(["blueberry", "tomato", "monstera"] as const).map((name, i) => (
              <span key={name} className="flex items-center">
                {i > 0 && <span className="mx-1.5 text-white/20">·</span>}
                <button
                  onClick={() => handleSearch(name)}
                  className="rounded px-1.5 py-0.5 text-white/55 transition-colors hover:bg-white/10 hover:text-white/90"
                >
                  {name}
                </button>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Results ─────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 pb-20 pt-10">
        {error && (
          <div className="mb-6 rounded-sm border border-red-200 bg-red-50 p-5 text-sm text-red-700">
            {error}
          </div>
        )}

        {warnings.length > 0 && (
          <div className="mb-6 rounded-sm border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            {warnings.join(" ")}
          </div>
        )}

        {loading && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {!loading && searched && !error && (
          <>
            {query && (
              <div className="mb-7 flex items-baseline justify-between gap-4">
                <div>
                  <h2 className="font-display text-3xl font-light text-ink">
                    Results for{" "}
                    <em className="italic text-fern">"{query}"</em>
                  </h2>
                  <p className="mt-1 flex items-center gap-2 text-sm text-ink-muted">
                    <span>{plants.length} species found</span>
                    {cacheHit !== null && (
                      <span className="rounded-full border border-border-plant bg-mist px-2 py-0.5 text-xs font-medium">
                        cache {cacheHit ? "hit" : "miss"}
                      </span>
                    )}
                  </p>
                </div>
              </div>
            )}

            {plants.length > 0 && (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {plants.map((plant, i) => (
                  <div
                    key={plant.slug || plant.id || plant.scientific_name}
                    className="animate-fade-up"
                    style={{ animationDelay: `${i * 35}ms` }}
                  >
                    <PlantCard plant={plant} />
                  </div>
                ))}
              </div>
            )}

            {plants.length === 0 && query && (
              <div className="rounded-sm border border-border-plant bg-parchment p-12 text-center">
                <p className="font-display text-2xl font-light italic text-ink-muted">
                  No specimens found for "{query}"
                </p>
                <p className="mt-2 text-sm text-ink-muted">
                  Try a different common or scientific name.
                </p>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}
