"use client";

import { FormEvent, useState } from "react";

export default function SearchBar({
  initialQuery = "",
  onSearch,
}: {
  initialQuery?: string;
  onSearch: (query: string) => void;
}) {
  const [query, setQuery] = useState(initialQuery);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();

    const cleaned = query.trim();
    if (!cleaned) return;

    onSearch(cleaned);
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-2xl gap-3">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search blueberry, monstera, tomato..."
        className="min-w-0 flex-1 rounded-xl border border-neutral-300 px-4 py-3 outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
      />

      <button
        type="submit"
        className="rounded-xl bg-green-700 px-5 py-3 font-medium text-white transition hover:bg-green-800"
      >
        Search
      </button>
    </form>
  );
}