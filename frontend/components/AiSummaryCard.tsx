"use client";

import { useEffect, useState } from "react";
import type { AiSummaryPayload } from "@/lib/ai";

type LoadState =
  | { status: "idle" | "loading" }
  | { status: "ready"; data: AiSummaryPayload }
  | { status: "error"; message: string };

export default function AiSummaryCard({
  title = "AI overview",
  subtitle,
  loadKey,
  loader,
}: {
  title?: string;
  subtitle?: string;
  /** Change this to re-trigger a fetch (e.g. query or slug). */
  loadKey: string;
  loader: () => Promise<AiSummaryPayload>;
}) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    loader()
      .then((data) => {
        if (!cancelled) setState({ status: "ready", data });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            status: "error",
            message:
              err instanceof Error ? err.message : "Could not generate summary",
          });
        }
      });

    return () => {
      cancelled = true;
    };
    // loader intentionally omitted — callers should encode inputs in loadKey
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadKey]);

  return (
    <section className="rounded-sm border border-ai-border bg-ai-panel p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
            <p className="font-sans text-[10px] font-semibold uppercase tracking-[0.16em] text-fern">
              {title}
            </p>
            {(state.status === "ready" ? state.data.model : null) && (
              <span className="rounded-sm border border-ai-border bg-white/50 px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-normal text-ink-muted normal-case">
                {state.status === "ready" ? state.data.model : null}
              </span>
            )}
            {state.status === "loading" && (
              <span className="rounded-sm border border-ai-border bg-white/40 px-1.5 py-0.5 font-mono text-[10px] text-ink-muted/70 normal-case">
                …
              </span>
            )}
          </div>
          {subtitle && (
            <p className="mt-1 font-sans text-sm text-ink-muted">{subtitle}</p>
          )}
        </div>
        <p className="font-sans text-[10px] font-medium uppercase tracking-[0.12em] text-ink-muted">
          May supplement incomplete Trefle data
        </p>
      </div>

      <p className="mt-3 rounded-sm border border-ai-border/80 bg-white/35 px-3 py-2 font-sans text-xs leading-relaxed text-ink-muted">
        AI-generated summaries are not 100% accurate — treat them as a starting
        point and verify important details against the Overview fields.
      </p>

      {state.status === "loading" && (
        <div className="mt-5 space-y-3">
          <div className="h-4 w-full max-w-3xl rounded shimmer" />
          <div className="h-4 w-[92%] max-w-2xl rounded shimmer" />
          <div className="h-4 w-[80%] max-w-xl rounded shimmer" />
        </div>
      )}

      {state.status === "error" && (
        <p className="mt-5 font-sans text-sm text-ink-muted">
          AI overview unavailable: {state.message}
        </p>
      )}

      {state.status === "ready" && (
        <p className="mt-5 whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
          {state.data.summary}
        </p>
      )}
    </section>
  );
}
