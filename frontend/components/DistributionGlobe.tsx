"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import { resolvePlaces, type GeoPoint, NATIVE_COLOR, INTRODUCED_COLOR } from "@/lib/geo";

type Marker = GeoPoint & {
  size: number;
  color: string;
  kind: "native" | "introduced";
};

/** Closed ring of points at latitude 0 for a dashed equator path */
const EQUATOR_PATH = [
  {
    name: "Equator",
    coords: Array.from({ length: 181 }, (_, i) => {
      const lng = -180 + i * 2;
      return [lng, 0] as [number, number];
    }),
  },
];

export default function DistributionGlobe({
  nativePlaces,
  introducedPlaces = [],
  label = "Distribution globe",
}: {
  nativePlaces: string[];
  introducedPlaces?: string[];
  label?: string;
}) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 560, height: 360 });
  const [markers, setMarkers] = useState<Marker[]>([]);
  const [unresolved, setUnresolved] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const placesKey = useMemo(
    () =>
      JSON.stringify({
        native: nativePlaces,
        introduced: introducedPlaces,
      }),
    [nativePlaces, introducedPlaces]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    function measure() {
      if (!el) return;
      const width = el.clientWidth;
      setSize({ width, height: Math.max(300, Math.round(width * 0.62)) });
    }

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    const parsed = JSON.parse(placesKey) as {
      native: string[];
      introduced: string[];
    };

    async function load() {
      if (!parsed.native.length && !parsed.introduced.length) {
        setMarkers([]);
        setUnresolved([]);
        setLoading(false);
        return;
      }

      setLoading(true);

      const [nativeRes, introducedRes] = await Promise.all([
        parsed.native.length
          ? resolvePlaces(parsed.native)
          : Promise.resolve({ points: [] as GeoPoint[], unresolved: [] as string[] }),
        parsed.introduced.length
          ? resolvePlaces(parsed.introduced)
          : Promise.resolve({ points: [] as GeoPoint[], unresolved: [] as string[] }),
      ]);

      if (cancelled) return;

      const next: Marker[] = [
        ...nativeRes.points.map((p) => ({
          ...p,
          size: 0.45,
          color: NATIVE_COLOR,
          kind: "native" as const,
        })),
        ...introducedRes.points.map((p) => ({
          ...p,
          size: 0.4,
          color: INTRODUCED_COLOR,
          kind: "introduced" as const,
        })),
      ];

      setMarkers(next);
      setUnresolved([...nativeRes.unresolved, ...introducedRes.unresolved]);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [placesKey]);

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe || !markers.length) return;

    const avgLat = markers.reduce((s, m) => s + m.lat, 0) / markers.length;
    const avgLng = markers.reduce((s, m) => s + m.lng, 0) / markers.length;

    globe.pointOfView({ lat: avgLat, lng: avgLng, altitude: 1.8 }, 1000);

    const controls = globe.controls();
    if (controls) {
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.45;
      controls.enableZoom = true;
    }
  }, [markers]);

  if (!nativePlaces.length && !introducedPlaces.length) {
    return (
      <div className="rounded-sm border border-border-plant bg-mist p-8 text-center text-sm text-ink-muted">
        No distribution data available for the globe.
      </div>
    );
  }

  const nativeCount = markers.filter((m) => m.kind === "native").length;
  const introducedCount = markers.filter((m) => m.kind === "introduced").length;

  return (
    <div className="overflow-hidden rounded-sm border border-border-plant bg-[#0b1a12]">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
        <p className="font-sans text-xs font-semibold uppercase tracking-[0.16em] text-leaf">
          {label}
        </p>
        <div className="flex items-center gap-3 text-xs text-white/50">
          <span className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: NATIVE_COLOR }}
            />
            Native {loading ? "…" : nativeCount}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: INTRODUCED_COLOR }}
            />
            Introduced {loading ? "…" : introducedCount}
          </span>
        </div>
      </div>

      <div ref={containerRef} className="relative w-full">
        {loading && markers.length === 0 ? (
          <div
            className="flex items-center justify-center text-sm text-white/60"
            style={{ height: size.height }}
          >
            Geocoding distribution…
          </div>
        ) : markers.length > 0 ? (
          <Globe
            ref={globeRef}
            width={size.width}
            height={size.height}
            backgroundColor="rgba(0,0,0,0)"
            globeImageUrl="//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
            bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
            pointsData={markers}
            pointLat="lat"
            pointLng="lng"
            pointAltitude={0.01}
            pointRadius="size"
            pointColor="color"
            pointLabel={(d) => {
              const m = d as Marker;
              return `${m.name} (${m.kind})`;
            }}
            pathsData={EQUATOR_PATH}
            pathPoints="coords"
            pathPointLng={(p) => (p as [number, number])[0]}
            pathPointLat={(p) => (p as [number, number])[1]}
            pathPointAlt={0.002}
            pathColor={() => "#EF4444"}
            pathStroke={0.6}
            pathDashLength={0.02}
            pathDashGap={0.015}
            pathDashAnimateTime={0}
            atmosphereColor="#6BB87A"
            atmosphereAltitude={0.18}
          />
        ) : (
          <div
            className="flex items-center justify-center px-6 text-center text-sm text-white/60"
            style={{ height: size.height }}
          >
            Could not geocode these place names yet.
          </div>
        )}
      </div>

      {!loading && unresolved.length > 0 && (
        <div className="border-t border-white/10 px-4 py-3 text-xs text-white/45">
          Unmapped places: {unresolved.join(", ")}
        </div>
      )}
    </div>
  );
}

