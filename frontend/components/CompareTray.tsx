"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  COMPARE_MAX,
  COMPARE_MIN,
  compareHref,
  getCompareList,
  removeFromCompare,
  type ComparePlantRef,
} from "@/lib/compare";

export default function CompareTray() {
  const [plants, setPlants] = useState<ComparePlantRef[]>([]);
  const trayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function sync() {
      setPlants(getCompareList());
    }

    sync();
    window.addEventListener("plantdex:compare-updated", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("plantdex:compare-updated", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  useEffect(() => {
    const root = document.documentElement;

    function clearPad() {
      root.style.setProperty("--compare-tray-pad", "0px");
    }

    if (plants.length === 0) {
      clearPad();
      return clearPad;
    }

    function measure() {
      const height = trayRef.current?.offsetHeight ?? 0;
      // Extra breathing room so last sections aren't flush against the tray
      root.style.setProperty("--compare-tray-pad", `${height + 24}px`);
    }

    measure();
    const observer = new ResizeObserver(measure);
    if (trayRef.current) observer.observe(trayRef.current);
    window.addEventListener("resize", measure);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", measure);
      clearPad();
    };
  }, [plants.length]);

  if (plants.length === 0) return null;

  const ready = plants.length >= COMPARE_MIN;

  return (
    <div
      ref={trayRef}
      className="fixed inset-x-0 bottom-0 z-50 border-t border-border-plant bg-parchment/95 backdrop-blur-md"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <p className="font-sans text-xs font-semibold uppercase tracking-[0.16em] text-fern">
            Compare tray · {plants.length}/{COMPARE_MAX}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {plants.map((plant) => (
              <button
                key={plant.slug}
                type="button"
                onClick={() => setPlants(removeFromCompare(plant.slug))}
                className="group inline-flex items-center gap-2 rounded-full border border-border-plant bg-mist px-3 py-1.5 text-left text-sm text-ink transition-colors hover:border-fern"
                title="Remove from compare"
              >
                <span className="max-w-[10rem] truncate">
                  {plant.common_name || plant.scientific_name || plant.slug}
                </span>
                <span className="text-ink-muted group-hover:text-fern">×</span>
              </button>
            ))}
          </div>
          {!ready && (
            <p className="mt-2 text-xs text-ink-muted">
              Select at least {COMPARE_MIN} plants to compare.
            </p>
          )}
        </div>

        <Link
          href={ready ? compareHref(plants.map((p) => p.slug)) : "/compare"}
          aria-disabled={!ready}
          className={`inline-flex items-center justify-center rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors ${
            ready
              ? "bg-fern text-white hover:bg-canopy"
              : "pointer-events-none bg-border-plant text-ink-muted"
          }`}
        >
          Compare plants
        </Link>
      </div>
    </div>
  );
}
