"use client";

import { useState } from "react";

type Field = {
  name: string;
  label: string;
  required?: boolean;
  placeholder?: string;
  defaultValue?: string;
  kind?: "text" | "select" | "textarea";
  options?: string[];
  detail?: string;
};

type Endpoint = {
  id: string;
  method: "GET" | "POST";
  path: string;
  summary: string;
  fields: Field[];
  /** Optional note shown above the run button */
  caution?: string;
  /** When true, show a static example instead of calling the live API */
  demoOnly?: boolean;
  exampleRequest?: string;
  exampleResponse?: string;
  buildRequest: (values: Record<string, string>) => {
    url: string;
    init?: RequestInit;
  };
};

function getApiBaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_PLANTDEX_API_URL;
  if (!url) return "";
  return url.replace(/\/$/, "");
}

const ENDPOINTS: Endpoint[] = [
  {
    id: "search",
    method: "GET",
    path: "/search",
    summary: "Search plants by common or scientific name.",
    fields: [
      {
        name: "query",
        label: "query",
        required: true,
        defaultValue: "blueberry",
        detail: "Search string",
      },
      {
        name: "max_results",
        label: "max_results",
        defaultValue: "3",
        detail: "Keep small for demos",
      },
      {
        name: "image_only",
        label: "image_only",
        kind: "select",
        options: ["false", "true"],
        defaultValue: "false",
      },
    ],
    buildRequest: (v) => {
      const params = new URLSearchParams({
        query: v.query || "blueberry",
        max_results: v.max_results || "3",
        image_only: v.image_only || "false",
      });
      return { url: `${getApiBaseUrl()}/search?${params}` };
    },
  },
  {
    id: "profile",
    method: "GET",
    path: "/plants/{slug}",
    summary: "Fetch a full plant profile for a Trefle slug.",
    fields: [
      {
        name: "slug",
        label: "slug",
        required: true,
        defaultValue: "vaccinium-corymbosum",
        detail: "Path parameter",
      },
    ],
    buildRequest: (v) => ({
      url: `${getApiBaseUrl()}/plants/${encodeURIComponent(
        v.slug || "vaccinium-corymbosum"
      )}`,
    }),
  },
  {
    id: "similar",
    method: "GET",
    path: "/similar",
    summary: "Return related plants using a similarity basis.",
    fields: [
      {
        name: "query",
        label: "query",
        required: true,
        defaultValue: "vaccinium-corymbosum",
      },
      {
        name: "basis",
        label: "basis",
        kind: "select",
        options: [
          "genus",
          "family",
          "distribution",
          "edible_part",
          "growth_habit",
          "growth_form",
          "fruit_color",
        ],
        defaultValue: "genus",
      },
      {
        name: "max_results",
        label: "max_results",
        defaultValue: "3",
      },
    ],
    buildRequest: (v) => {
      const params = new URLSearchParams({
        query: v.query || "vaccinium-corymbosum",
        basis: v.basis || "genus",
        max_results: v.max_results || "3",
        image_only: "false",
      });
      return { url: `${getApiBaseUrl()}/similar?${params}` };
    },
  },
  {
    id: "report",
    method: "POST",
    path: "/plants/{slug}/report",
    summary: "Proxy an error report to Trefle (token stays on the server).",
    demoOnly: true,
    caution:
      "Live run is disabled here so Trefle isn’t flooded by playground traffic. Use the profile page form when you truly need to report something.",
    fields: [
      {
        name: "slug",
        label: "slug",
        required: true,
        defaultValue: "vaccinium-corymbosum",
      },
      {
        name: "notes",
        label: "notes",
        kind: "textarea",
        required: true,
        defaultValue: "The maximum height on this record looks incorrect.",
      },
    ],
    exampleRequest: `{
  "notes": "The maximum height on this record looks incorrect.",
  "species_id": "vaccinium-corymbosum"
}`,
    exampleResponse: `{
  "ok": true,
  "type": "report",
  "species_id": "vaccinium-corymbosum",
  "trefle": {
    "id": 9,
    "record_type": "Species",
    "warning_type": "report",
    "change_status": "pending",
    "notes": "The maximum height on this record looks incorrect."
  }
}`,
    buildRequest: (v) => ({
      url: `${getApiBaseUrl()}/plants/${encodeURIComponent(
        v.slug || "vaccinium-corymbosum"
      )}/report`,
      init: {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notes: v.notes || "Example report notes",
          species_id: v.slug || "vaccinium-corymbosum",
        }),
      },
    }),
  },
  {
    id: "corrections",
    method: "POST",
    path: "/plants/{slug}/corrections",
    summary: "Proxy a field correction to Trefle for peer review.",
    demoOnly: true,
    caution:
      "Live run is disabled here so Trefle isn’t flooded by playground traffic. Use the profile page form for real corrections.",
    fields: [
      {
        name: "slug",
        label: "slug",
        required: true,
        defaultValue: "vaccinium-corymbosum",
      },
      {
        name: "field",
        label: "correction field",
        kind: "select",
        options: ["observations", "common_name", "growth_habit", "fruit_color"],
        defaultValue: "observations",
      },
      {
        name: "value",
        label: "new value",
        defaultValue: "Native to eastern North America",
      },
      {
        name: "source_type",
        label: "source_type",
        kind: "select",
        options: ["external", "publication", "user_observation"],
        defaultValue: "external",
      },
      {
        name: "source_reference",
        label: "source_reference",
        defaultValue: "https://example.org/botany-source",
      },
      {
        name: "notes",
        label: "notes",
        kind: "textarea",
        defaultValue: "Updating observations from a trusted reference.",
      },
    ],
    exampleRequest: `{
  "notes": "Updating observations from a trusted reference.",
  "source_type": "external",
  "source_reference": "https://example.org/botany-source",
  "species_id": "vaccinium-corymbosum",
  "correction": {
    "observations": "Native to eastern North America"
  }
}`,
    exampleResponse: `{
  "ok": true,
  "type": "correction",
  "species_id": "vaccinium-corymbosum",
  "trefle": {
    "id": 8,
    "record_type": "Species",
    "change_status": "pending",
    "change_type": "update",
    "notes": "Updating observations from a trusted reference.",
    "correction": {
      "observations": "Native to eastern North America"
    }
  }
}`,
    buildRequest: (v) => {
      const field = v.field || "observations";
      return {
        url: `${getApiBaseUrl()}/plants/${encodeURIComponent(
          v.slug || "vaccinium-corymbosum"
        )}/corrections`,
        init: {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            notes: v.notes || "Example correction notes",
            source_type: v.source_type || "external",
            source_reference: v.source_reference || "https://example.org/botany-source",
            species_id: v.slug || "vaccinium-corymbosum",
            correction: {
              [field]: v.value || "Native to eastern North America",
            },
          }),
        },
      };
    },
  },
];

function defaultsFor(endpoint: Endpoint): Record<string, string> {
  const values: Record<string, string> = {};
  for (const field of endpoint.fields) {
    values[field.name] = field.defaultValue ?? "";
  }
  return values;
}

function EndpointCard({ endpoint }: { endpoint: Endpoint }) {
  const [values, setValues] = useState(() => defaultsFor(endpoint));
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [responseText, setResponseText] = useState("");
  const [error, setError] = useState("");

  const preview = endpoint.buildRequest(values);
  const isDemoOnly = Boolean(endpoint.demoOnly);

  async function run() {
    if (isDemoOnly) return;

    if (!getApiBaseUrl()) {
      setError("Missing NEXT_PUBLIC_PLANTDEX_API_URL in this environment.");
      return;
    }

    setLoading(true);
    setError("");
    setStatus(null);
    setElapsedMs(null);
    setResponseText("");

    const started = performance.now();
    try {
      const { url, init } = endpoint.buildRequest(values);
      const res = await fetch(url, { ...init, cache: "no-store" });
      const text = await res.text();
      setElapsedMs(Math.round(performance.now() - started));
      setStatus(res.status);

      try {
        setResponseText(JSON.stringify(JSON.parse(text), null, 2));
      } catch {
        setResponseText(text || "(empty response body)");
      }

      if (!res.ok) {
        setError(`Request finished with HTTP ${res.status}`);
      }
    } catch (err) {
      setElapsedMs(Math.round(performance.now() - started));
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <article className="rounded-sm border border-border-plant bg-parchment p-6">
      <div className="flex flex-wrap items-baseline gap-3">
        <span className="rounded-full border border-fern/40 bg-mist px-2.5 py-0.5 font-sans text-xs font-semibold uppercase tracking-wider text-fern">
          {endpoint.method}
        </span>
        <code className="font-sans text-sm font-medium text-ink">
          {endpoint.path}
        </code>
        {isDemoOnly && (
          <span className="rounded-full border border-border-plant bg-mist px-2.5 py-0.5 font-sans text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
            Example only
          </span>
        )}
      </div>
      <p className="mt-3 text-sm text-ink-muted">{endpoint.summary}</p>
      {endpoint.caution && (
        <p className="mt-3 rounded-sm border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {endpoint.caution}
        </p>
      )}

      {!isDemoOnly && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {endpoint.fields.map((field) => (
            <label
              key={field.name}
              className={`block text-sm ${
                field.kind === "textarea" ? "sm:col-span-2" : ""
              }`}
            >
              <span className="mb-1.5 flex items-center gap-2 font-sans text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
                {field.label}
                {field.required && (
                  <span className="normal-case tracking-normal">required</span>
                )}
              </span>
              {field.kind === "select" ? (
                <select
                  value={values[field.name] ?? ""}
                  onChange={(e) =>
                    setValues((prev) => ({
                      ...prev,
                      [field.name]: e.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-border-plant bg-mist px-3 py-2.5 text-ink outline-none focus:border-fern"
                >
                  {(field.options || []).map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : field.kind === "textarea" ? (
                <textarea
                  value={values[field.name] ?? ""}
                  onChange={(e) =>
                    setValues((prev) => ({
                      ...prev,
                      [field.name]: e.target.value,
                    }))
                  }
                  rows={3}
                  className="w-full rounded-lg border border-border-plant bg-mist px-3 py-2.5 text-ink outline-none focus:border-fern"
                />
              ) : (
                <input
                  value={values[field.name] ?? ""}
                  onChange={(e) =>
                    setValues((prev) => ({
                      ...prev,
                      [field.name]: e.target.value,
                    }))
                  }
                  placeholder={field.placeholder}
                  className="w-full rounded-lg border border-border-plant bg-mist px-3 py-2.5 text-ink outline-none focus:border-fern"
                />
              )}
              {field.detail && (
                <span className="mt-1 block text-xs text-ink-muted">
                  {field.detail}
                </span>
              )}
            </label>
          ))}
        </div>
      )}

      <div className="mt-4 rounded-sm border border-dashed border-border-plant bg-mist/60 px-3 py-2">
        <p className="font-sans text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
          {isDemoOnly ? "Example request" : "Request URL"}
        </p>
        {isDemoOnly ? (
          <pre className="mt-2 overflow-auto font-mono text-xs leading-relaxed text-ink">
            {endpoint.method} {endpoint.path}
            {"\n\n"}
            {endpoint.exampleRequest}
          </pre>
        ) : (
          <code className="mt-1 block break-all font-sans text-xs text-ink">
            {endpoint.method} {preview.url || "(set NEXT_PUBLIC_PLANTDEX_API_URL)"}
          </code>
        )}
      </div>

      {!isDemoOnly && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={run}
            disabled={loading}
            className="rounded-lg bg-fern px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-canopy disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Running…" : "Run API"}
          </button>
          {status !== null && (
            <span className="font-sans text-xs text-ink-muted">
              HTTP {status}
              {elapsedMs !== null ? ` · ${elapsedMs} ms` : ""}
            </span>
          )}
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-sm border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {(isDemoOnly || responseText || loading) && (
        <div className="mt-4">
          <p className="mb-2 font-sans text-[10px] font-semibold uppercase tracking-widest text-ink-muted">
            {isDemoOnly ? "Example JSON response" : "Raw JSON response"}
          </p>
          <pre className="max-h-[28rem] overflow-auto rounded-sm border border-border-plant bg-[#0b1a12] p-4 font-mono text-xs leading-relaxed text-leaf">
            {isDemoOnly
              ? endpoint.exampleResponse
              : loading && !responseText
                ? "Waiting for response…"
                : responseText}
          </pre>
        </div>
      )}
    </article>
  );
}

export default function ApiPlayground() {
  return (
    <section className="mt-14">
      <h2 className="font-display text-3xl font-light text-ink">Backend APIs</h2>
      <p className="mt-2 max-w-2xl text-sm text-ink-muted">
        Read endpoints can be run live against the real backend — edit the inputs
        and hit <span className="font-medium text-ink">Run API</span> to inspect
        raw JSON. Report and correction endpoints are example-only so Trefle
        doesn’t get accidental playground traffic.
      </p>

      <div className="mt-8 space-y-5">
        {ENDPOINTS.map((endpoint) => (
          <EndpointCard key={endpoint.id} endpoint={endpoint} />
        ))}
      </div>
    </section>
  );
}
