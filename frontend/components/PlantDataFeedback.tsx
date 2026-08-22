"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  reportPlantError,
  submitPlantCorrection,
  type PlantProfile,
} from "@/lib/api";

const CORRECTION_FIELDS: { value: string; label: string }[] = [
  { value: "common_name", label: "Common name" },
  { value: "scientific_name", label: "Scientific name" },
  { value: "observations", label: "Observations" },
  { value: "author", label: "Author" },
  { value: "bibliography", label: "Bibliography" },
  { value: "duration", label: "Duration" },
  { value: "edible_part", label: "Edible part" },
  { value: "vegetable", label: "Vegetable (true/false)" },
  { value: "flower_color", label: "Flower color" },
  { value: "foliage_color", label: "Foliage color" },
  { value: "fruit_color", label: "Fruit color" },
  { value: "growth_habit", label: "Growth habit" },
  { value: "growth_form", label: "Growth form" },
  { value: "growth_rate", label: "Growth rate" },
  { value: "toxicity", label: "Toxicity" },
  { value: "light", label: "Light (0–10)" },
  { value: "ph_minimum", label: "pH minimum" },
  { value: "ph_maximum", label: "pH maximum" },
  { value: "average_height_value", label: "Average height value" },
  { value: "average_height_unit", label: "Average height unit (cm/m)" },
  { value: "maximum_height_value", label: "Maximum height value" },
  { value: "maximum_height_unit", label: "Maximum height unit (cm/m)" },
];

function resolveSpeciesId(plant: PlantProfile): string {
  const raw = (plant.raw || {}) as Record<string, unknown>;
  const mainSpecies = (raw.main_species || {}) as Record<string, unknown>;
  const speciesSlug = mainSpecies.slug;
  if (typeof speciesSlug === "string" && speciesSlug.trim()) {
    return speciesSlug.trim();
  }
  if (typeof mainSpecies.id === "number" || typeof mainSpecies.id === "string") {
    return String(mainSpecies.id);
  }
  return String(plant.slug || "");
}

export default function PlantDataFeedback({ plant }: { plant: PlantProfile }) {
  const slug = plant.slug || "";
  const speciesId = useMemo(() => resolveSpeciesId(plant), [plant]);
  const [mode, setMode] = useState<"report" | "correction">("report");
  const [notes, setNotes] = useState("");
  const [sourceType, setSourceType] = useState<
    "external" | "user_observation" | "publication"
  >("external");
  const [sourceReference, setSourceReference] = useState("");
  const [field, setField] = useState(CORRECTION_FIELDS[0].value);
  const [fieldValue, setFieldValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!slug) {
      setError("Missing plant slug.");
      return;
    }

    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      if (mode === "report") {
        await reportPlantError({ slug, speciesId, notes });
        setSuccess("Thanks — your error report was sent to Trefle for review.");
        setNotes("");
      } else {
        let parsed: string | number | boolean = fieldValue;
        if (fieldValue === "true" || fieldValue === "false") {
          parsed = fieldValue === "true";
        } else if (fieldValue.trim() !== "" && !Number.isNaN(Number(fieldValue))) {
          // Keep IDs/heights numeric when clearly numeric
          if (
            field.includes("height") ||
            field.includes("ph_") ||
            field === "light" ||
            field.includes("temperature")
          ) {
            parsed = Number(fieldValue);
          }
        }

        await submitPlantCorrection({
          slug,
          speciesId,
          notes,
          sourceType,
          sourceReference,
          correction: { [field]: parsed },
        });
        setSuccess("Thanks — your correction was submitted to Trefle for peer review.");
        setNotes("");
        setSourceReference("");
        setFieldValue("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mt-14 space-y-6 border-t border-dotted border-border-plant pt-14">
      <div
        role="note"
        aria-label="Disclaimer"
        className="rounded-sm border border-red-300 bg-red-50 px-5 py-4"
      >
        <p className="font-sans text-[10px] font-semibold uppercase tracking-[0.18em] text-red-700">
          Disclaimer
        </p>
        <p className="mt-2 font-sans text-sm leading-relaxed text-red-900/85">
          Plant data on this page is sourced from{" "}
          <a
            href="https://trefle.io"
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold underline decoration-red-300 underline-offset-2 hover:text-red-950"
          >
            Trefle
          </a>
          . Trefle’s database is community-sourced and may contain incomplete or
          incorrect information. Use the form below to report an error or submit
          a correction directly to Trefle.
        </p>
      </div>

      <div className="rounded-sm border border-border-plant bg-parchment p-6">
        <h3 className="font-display text-2xl font-light text-ink">
          Help improve this plant’s data
        </h3>
        <p className="mt-2 text-sm text-ink-muted">
          Submissions are proxied securely to Trefle and reviewed by their
          community. Species ID:{" "}
          <span className="font-medium text-ink">{speciesId || "unknown"}</span>
        </p>

        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={() => {
              setMode("report");
              setError("");
              setSuccess("");
            }}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
              mode === "report"
                ? "bg-fern text-white"
                : "border border-border-plant bg-mist text-ink-muted hover:text-ink"
            }`}
          >
            Report an error
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("correction");
              setError("");
              setSuccess("");
            }}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
              mode === "correction"
                ? "bg-fern text-white"
                : "border border-border-plant bg-mist text-ink-muted hover:text-ink"
            }`}
          >
            Submit a correction
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {mode === "correction" && (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm">
                  <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
                    Field to correct
                  </span>
                  <select
                    value={field}
                    onChange={(e) => setField(e.target.value)}
                    className="w-full rounded-lg border border-border-plant bg-mist px-3 py-2.5 text-ink outline-none focus:border-fern"
                  >
                    {CORRECTION_FIELDS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block text-sm">
                  <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
                    New value
                  </span>
                  <input
                    value={fieldValue}
                    onChange={(e) => setFieldValue(e.target.value)}
                    required
                    placeholder="e.g. red, shrub, 150…"
                    className="w-full rounded-lg border border-border-plant bg-mist px-3 py-2.5 text-ink outline-none focus:border-fern"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm">
                  <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
                    Source type
                  </span>
                  <select
                    value={sourceType}
                    onChange={(e) =>
                      setSourceType(
                        e.target.value as
                          | "external"
                          | "user_observation"
                          | "publication"
                      )
                    }
                    className="w-full rounded-lg border border-border-plant bg-mist px-3 py-2.5 text-ink outline-none focus:border-fern"
                  >
                    <option value="external">External reference</option>
                    <option value="publication">Publication</option>
                    <option value="user_observation">User observation</option>
                  </select>
                </label>

                <label className="block text-sm">
                  <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
                    Source reference
                  </span>
                  <input
                    value={sourceReference}
                    onChange={(e) => setSourceReference(e.target.value)}
                    required
                    placeholder="URL, citation, or observation details"
                    className="w-full rounded-lg border border-border-plant bg-mist px-3 py-2.5 text-ink outline-none focus:border-fern"
                  />
                </label>
              </div>
            </>
          )}

          <label className="block text-sm">
            <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
              {mode === "report" ? "Describe the error" : "Notes (optional)"}
            </span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              required={mode === "report"}
              rows={4}
              placeholder={
                mode === "report"
                  ? "What looks wrong on this plant record?"
                  : "Optional context for reviewers"
              }
              className="w-full rounded-lg border border-border-plant bg-mist px-3 py-2.5 text-ink outline-none focus:border-fern"
            />
          </label>

          {error && (
            <div className="rounded-sm border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}
          {success && (
            <div className="rounded-sm border border-leaf/50 bg-mist px-4 py-3 text-sm text-fern">
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !slug}
            className="rounded-lg bg-fern px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-canopy disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting
              ? "Sending to Trefle…"
              : mode === "report"
                ? "Send error report"
                : "Submit correction"}
          </button>
        </form>
      </div>
    </section>
  );
}
