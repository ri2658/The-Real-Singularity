import { Suspense } from "react";
import ComparePage from "./CompareClient";

export default function Page() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-mist px-6 py-16">
          <div className="mx-auto max-w-6xl">
            <div className="h-10 w-64 rounded shimmer" />
            <div className="mt-6 h-64 rounded-sm border border-border-plant bg-parchment shimmer" />
          </div>
        </main>
      }
    >
      <ComparePage />
    </Suspense>
  );
}
