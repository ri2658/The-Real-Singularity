"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import { resolvePlaces, type GeoPoint } from "@/lib/geo";

type Marker = GeoPoint & {
  size: number;
  color: string;
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
  places,
  label = "Native range",
}: {
  places: string[];
  label?: string;
}) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 560, height: 360 });
  const [markers, setMarkers] = useState<Marker[]>([]);
  const [unresolved, setUnresolved] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const placesKey = useMemo(() => places.join("|"), [places]);

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
    const names = placesKey ? placesKey.split("|") : [];

    async function load() {
      if (!names.length) {
        setMarkers([]);
        setUnresolved([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      const { points, unresolved: missed } = await resolvePlaces(names);
      if (cancelled) return;

      setMarkers(
        points.map((p) => ({
          ...p,
          size: 0.45,
          color: "#6BB87A",
        }))
      );
      setUnresolved(missed);
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

  if (!places.length) {
    return (
      <div className="rounded-sm border border-border-plant bg-mist p-8 text-center text-sm text-ink-muted">
        No distribution data available for the globe.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-sm border border-border-plant bg-[#0b1a12]">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <p className="font-sans text-xs font-semibold uppercase tracking-[0.16em] text-leaf">
          {label}
        </p>
        <p className="text-xs text-white/50">
          {loading
            ? "Locating regions…"
            : `${markers.length} mapped${
                unresolved.length ? ` · ${unresolved.length} unmapped` : ""
              }`}
        </p>
      </div>

      <div ref={containerRef} className="relative w-full">
        {loading && markers.length === 0 ? (
          <div
            className="flex items-center justify-center text-sm text-white/60"
            style={{ height: size.height }}
          >
            Geocoding native range…
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
            pointLabel={(d) => (d as Marker).name}
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
