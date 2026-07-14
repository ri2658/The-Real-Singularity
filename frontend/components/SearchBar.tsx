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
    <form onSubmit={handleSubmit} className="flex w-full max-w-2xl gap-2">
      <div className="relative flex-1 rounded-lg focus-within:ring-2 focus-within:ring-sprout/40 transition-shadow duration-200">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search blueberry, monstera, tomato…"
          className="w-full rounded-lg border border-white/20 bg-white/10 px-4 py-3.5 text-white placeholder:text-white/40 outline-none backdrop-blur-sm transition-colors duration-200 focus:border-white/40 focus:bg-white/15"
        />
      </div>
      <button
        type="submit"
        className="rounded-lg bg-sprout px-6 py-3.5 font-semibold text-forest transition-colors duration-200 hover:bg-leaf"
      >
        Search
      </button>
    </form>
  );
}
